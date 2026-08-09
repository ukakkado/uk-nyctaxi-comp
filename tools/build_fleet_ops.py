"""Build the fleet operator's own operational source system.

Context: the warehouse already lands TLC trip records. Those records describe
the *journey* but carry no identity -- no driver, no vehicle, no shift. The
operator (Harbour Point Taxi Management, a medallion fleet and garage business)
runs its own dispatch and telematics platform, and that platform is a second
source system landing into `ops_raw`.

Everything here is derived deterministically from the real TLC trips, so the
result is reproducible and internally consistent: a vehicle is never on two
trips at once, a shift never contains a trip outside its window, and the status
event stream reconciles to the trips it brackets.

Deliberate imperfections, because a real telematics feed has them:
  * a small share of shifts never emit a LOGOUT (tablet died mid-shift)
  * a small share of status events arrive out of order
  * some trips are assigned to a shift whose window does not contain them
  * odometer readings are occasionally missing
These are flagged downstream, not cleaned here.
"""

import os
import duckdb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "domain.duckdb")

con = duckdb.connect(DB)
con.execute("CREATE OR REPLACE MACRO hb(x) AS CAST(hash(x) % 100000000 AS BIGINT)")
con.execute("CREATE SCHEMA IF NOT EXISTS ops_raw")

N_VEHICLES = 420
N_DRIVERS = 760
N_GARAGES = 6

# ---------------------------------------------------------------------------
# Reference entities. Deterministic; no RNG.
# ---------------------------------------------------------------------------

con.execute(
    f"""
    CREATE OR REPLACE TABLE ops_raw.garage AS
    SELECT * FROM (VALUES
        (1, 'Long Island City Depot',  'Queens',        140, DATE '2011-04-01'),
        (2, 'Sunset Park Yard',        'Brooklyn',      110, DATE '2013-09-15'),
        (3, 'Hunts Point Garage',      'Bronx',          80, DATE '2015-06-01'),
        (4, 'Willets Point Annex',     'Queens',         60, DATE '2019-02-11'),
        (5, 'Bay Ridge Overflow',      'Brooklyn',       40, DATE '2021-08-30'),
        (6, 'Harbour Point HQ Lot',    'Manhattan',      30, DATE '2009-01-01')
    ) t(garage_id, garage_name, borough, bay_capacity, opened_date)
    """
)

# Vehicles. Medallion numbers follow the real NYC format (e.g. 7X41).
con.execute(
    f"""
    CREATE OR REPLACE TABLE ops_raw.vehicle AS
    WITH v AS (SELECT unnest(generate_series(1, {N_VEHICLES})) AS n)
    SELECT
        n                                                       AS vehicle_id,
        format('{{:1d}}{{}}{{:02d}}',
               1 + (n % 9),
               chr((65 + (n * 7) % 26)::INTEGER),
               1 + (n % 99))                                    AS medallion_number,
        'HPT' || lpad((100000 + n * 37)::VARCHAR, 8, '0')        AS vin,
        CASE n % 5 WHEN 0 THEN 'Toyota' WHEN 1 THEN 'Nissan'
                   WHEN 2 THEN 'Toyota' WHEN 3 THEN 'Ford'
                   ELSE 'Chevrolet' END                         AS make,
        CASE n % 5 WHEN 0 THEN 'Camry Hybrid' WHEN 1 THEN 'NV200'
                   WHEN 2 THEN 'Sienna' WHEN 3 THEN 'Escape Hybrid'
                   ELSE 'Malibu' END                            AS model,
        2016 + (n % 8)                                          AS model_year,
        CASE WHEN n % 5 IN (0, 3) THEN 'hybrid'
             WHEN n % 23 = 0 THEN 'electric' ELSE 'gasoline' END AS fuel_type,
        (n % 9 = 0)                                             AS wheelchair_accessible,
        1 + (n % {N_GARAGES})                                   AS garage_id,
        DATE '2016-01-01' + INTERVAL (n * 11 % 2900) DAY         AS in_service_date,
        CASE WHEN n % 47 = 0
             THEN DATE '2024-01-01' + INTERVAL (n % 150) DAY
             ELSE NULL END                                      AS retired_date
    FROM v
    """
)

# Drivers. Hack licence numbers, hire dates, a realistic churn tail.
con.execute(
    f"""
    CREATE OR REPLACE TABLE ops_raw.driver AS
    WITH d AS (SELECT unnest(generate_series(1, {N_DRIVERS})) AS n)
    SELECT
        n                                                        AS driver_id,
        '5' || lpad((400000 + n * 13)::VARCHAR, 6, '0')          AS hack_licence_no,
        'DRV-' || lpad(n::VARCHAR, 4, '0')                       AS driver_ref,
        CASE n % 4 WHEN 0 THEN 'owner_operator' WHEN 1 THEN 'lease_daily'
                   WHEN 2 THEN 'lease_weekly' ELSE 'lease_daily' END AS engagement_type,
        1 + (n % {N_GARAGES})                                    AS home_garage_id,
        DATE '2012-01-01' + INTERVAL (n * 19 % 4300) DAY          AS hire_date,
        CASE WHEN n % 31 = 0
             THEN DATE '2024-02-01' + INTERVAL (n % 120) DAY
             ELSE NULL END                                       AS termination_date,
        (n % 6 = 0)                                              AS is_wav_certified,
        CASE WHEN n % 31 = 0 THEN 'terminated' ELSE 'active' END  AS driver_status
    FROM d
    """
)

con.execute(
    """
    CREATE OR REPLACE TABLE ops_raw.lease_agreement AS
    SELECT
        row_number() OVER (ORDER BY d.driver_id)                 AS lease_id,
        d.driver_id,
        1 + ((d.driver_id * 3) % (SELECT count(*) FROM ops_raw.vehicle)) AS primary_vehicle_id,
        d.engagement_type                                        AS lease_type,
        CASE d.engagement_type
             WHEN 'owner_operator' THEN 0.00
             WHEN 'lease_weekly'   THEN 830.00 + (d.driver_id % 7) * 10
             ELSE 129.00 + (d.driver_id % 5) * 6 END             AS lease_rate,
        CASE d.engagement_type
             WHEN 'owner_operator' THEN 0.12 ELSE 0.00 END       AS revenue_share_pct,
        greatest(d.hire_date, DATE '2022-01-01')                 AS lease_start_date,
        d.termination_date                                       AS lease_end_date
    FROM ops_raw.driver d
    """
)

# ---------------------------------------------------------------------------
# Attribution. Harbour Point runs ~420 medallions of roughly 13,000 city-wide,
# so it sees a slice of the yellow fleet's trips. Attribution is by hash bucket
# on the trip's own key, then made temporally consistent per vehicle.
# ---------------------------------------------------------------------------

con.execute(
    """
    CREATE OR REPLACE TEMP TABLE candidate_trips AS
    SELECT
        t.trip_key,
        t.pickup_datetime,
        t.dropoff_datetime,
        t.pickup_location_id,
        t.dropoff_location_id,
        t.total_amount,
        t.trip_distance,
        1 + (hb(t.trip_key) % 420)::INTEGER AS vehicle_id
    FROM silver.trips t
    WHERE t.service_type = 'yellow'
      AND hb(t.trip_key || 'harbourpoint') % 100 < 6
      AND t.pickup_datetime >= TIMESTAMP '2024-01-01'
      AND t.pickup_datetime <  TIMESTAMP '2024-07-01'
      AND t.dropoff_datetime > t.pickup_datetime
      AND t.dropoff_datetime < t.pickup_datetime + INTERVAL 6 HOUR
    """
)

# Drop any trip that overlaps the previous trip on the same vehicle. A medallion
# cannot be on two fares at once, and letting that through would make every
# occupancy number meaningless.
con.execute(
    """
    CREATE OR REPLACE TEMP TABLE fleet_trips AS
    WITH ordered AS (
        SELECT *,
               lag(dropoff_datetime) OVER (
                   PARTITION BY vehicle_id ORDER BY pickup_datetime
               ) AS prev_dropoff
        FROM candidate_trips
    )
    SELECT * EXCLUDE (prev_dropoff)
    FROM ordered
    WHERE prev_dropoff IS NULL OR pickup_datetime >= prev_dropoff
    """
)

# Shifts. Consecutive trips on one vehicle separated by less than five hours
# belong to the same shift; a longer gap starts a new one.
con.execute(
    """
    CREATE OR REPLACE TEMP TABLE trip_shift AS
    WITH gaps AS (
        SELECT *,
               CASE WHEN lag(dropoff_datetime) OVER w IS NULL
                      OR pickup_datetime - lag(dropoff_datetime) OVER w > INTERVAL 5 HOUR
                    THEN 1 ELSE 0 END AS is_shift_start
        FROM fleet_trips
        WINDOW w AS (PARTITION BY vehicle_id ORDER BY pickup_datetime)
    )
    SELECT *,
           sum(is_shift_start) OVER (
               PARTITION BY vehicle_id ORDER BY pickup_datetime
               ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
           ) AS shift_seq
    FROM gaps
    """
)

con.execute(
    """
    CREATE OR REPLACE TABLE ops_raw.shift AS
    WITH agg AS (
        SELECT vehicle_id,
               shift_seq,
               min(pickup_datetime)  AS first_trip_ts,
               max(dropoff_datetime) AS last_trip_ts,
               count(*)              AS trip_count,
               sum(trip_distance)    AS shift_miles
        FROM trip_shift
        GROUP BY 1, 2
    ),
    shaped AS (
        SELECT
            'SH-' || lpad((row_number() OVER (ORDER BY vehicle_id, shift_seq))::VARCHAR, 8, '0') AS shift_id,
            a.vehicle_id,
            a.shift_seq,
            -- The driver signs on some minutes before the first fare and signs
            -- off some minutes after the last one.
            a.first_trip_ts - INTERVAL 1 MINUTE * (7 + (hb(a.vehicle_id::VARCHAR || a.shift_seq::VARCHAR) % 38)) AS shift_start_ts,
            a.last_trip_ts  + INTERVAL 1 MINUTE * (4 + (hb(a.shift_seq::VARCHAR || a.vehicle_id::VARCHAR) % 26)) AS shift_end_ts,
            a.trip_count,
            a.shift_miles
        FROM agg a
    )
    SELECT
        s.shift_id,
        s.vehicle_id,
        -- Drivers have a home vehicle but cover others. Roughly four shifts in
        -- five go to the vehicle's regular driver.
        CASE WHEN hb(s.shift_id) % 5 < 4
             THEN 1 + ((s.vehicle_id * 7) % 760)
             ELSE 1 + (hb(s.shift_id || 'cover') % 760) END      AS driver_id,
        s.shift_start_ts,
        -- ~1.5% of shifts never close: the tablet lost power before LOGOUT.
        CASE WHEN hb(s.shift_id || 'close') % 200 < 3
             THEN NULL ELSE s.shift_end_ts END                     AS shift_end_ts,
        s.shift_end_ts                                             AS derived_end_ts,
        s.trip_count                                               AS reported_trip_count,
        round(12000 + (hb(s.shift_id) % 180000) / 1.0, 0)        AS odometer_start,
        CASE WHEN hb(s.shift_id || 'odo') % 50 = 0 THEN NULL
             ELSE round(12000 + (hb(s.shift_id) % 180000) + s.shift_miles, 0) END AS odometer_end,
        CASE WHEN hb(s.shift_id || 'src') % 100 < 92
             THEN 'tablet' ELSE 'driver_app' END                   AS telematics_source
    FROM shaped s
    """
)

con.execute(
    """
    CREATE OR REPLACE TABLE ops_raw.trip_assignment AS
    SELECT
        'TA-' || lpad((row_number() OVER (ORDER BY ts.vehicle_id, ts.pickup_datetime))::VARCHAR, 9, '0') AS assignment_id,
        ts.trip_key,
        sh.shift_id,
        sh.driver_id,
        ts.vehicle_id,
        ts.pickup_datetime AS assigned_ts,
        CASE WHEN hb(ts.trip_key || 'mtr') % 500 = 0
             THEN 'manual' ELSE 'auto' END AS assignment_method
    FROM trip_shift ts
    JOIN ops_raw.shift sh
      ON sh.vehicle_id = ts.vehicle_id
     AND sh.shift_start_ts <= ts.pickup_datetime
     AND coalesce(sh.shift_end_ts, sh.derived_end_ts) >= ts.dropoff_datetime
    """
)

# ---------------------------------------------------------------------------
# The driver status event stream. This is the occupancy source: a driver moves
# LOGIN -> AVAILABLE -> DISPATCHED -> ON_TRIP -> AVAILABLE ... -> LOGOUT, with
# BREAK and OFFLINE interleaved on longer gaps.
# ---------------------------------------------------------------------------

con.execute(
    """
    CREATE OR REPLACE TABLE ops_raw.driver_status_event AS
    WITH trip_events AS (
        SELECT ta.shift_id, ta.driver_id, ta.vehicle_id,
               ts.pickup_datetime - INTERVAL 3 MINUTE AS event_ts,
               'DISPATCHED' AS status_code, ts.pickup_location_id AS zone_id, 2 AS ord
        FROM ops_raw.trip_assignment ta
        JOIN trip_shift ts ON ts.trip_key = ta.trip_key
        UNION ALL
        SELECT ta.shift_id, ta.driver_id, ta.vehicle_id,
               ts.pickup_datetime, 'ON_TRIP', ts.pickup_location_id, 3
        FROM ops_raw.trip_assignment ta
        JOIN trip_shift ts ON ts.trip_key = ta.trip_key
        UNION ALL
        SELECT ta.shift_id, ta.driver_id, ta.vehicle_id,
               ts.dropoff_datetime, 'AVAILABLE', ts.dropoff_location_id, 4
        FROM ops_raw.trip_assignment ta
        JOIN trip_shift ts ON ts.trip_key = ta.trip_key
    ),
    bookend AS (
        SELECT s.shift_id, s.driver_id, s.vehicle_id, s.shift_start_ts AS event_ts,
               'LOGIN' AS status_code, NULL::INTEGER AS zone_id, 1 AS ord
        FROM ops_raw.shift s
        UNION ALL
        SELECT s.shift_id, s.driver_id, s.vehicle_id, s.shift_start_ts + INTERVAL 1 MINUTE,
               'AVAILABLE', NULL, 1
        FROM ops_raw.shift s
        UNION ALL
        SELECT s.shift_id, s.driver_id, s.vehicle_id, s.shift_end_ts,
               'LOGOUT', NULL, 9
        FROM ops_raw.shift s
        WHERE s.shift_end_ts IS NOT NULL
    ),
    breaks AS (
        -- A gap of more than 25 minutes between fares is recorded as a break.
        SELECT ta.shift_id, ta.driver_id, ta.vehicle_id,
               ts.dropoff_datetime + INTERVAL 1 MINUTE AS event_ts,
               'BREAK' AS status_code, ts.dropoff_location_id AS zone_id, 5 AS ord
        FROM ops_raw.trip_assignment ta
        JOIN trip_shift ts ON ts.trip_key = ta.trip_key
        QUALIFY lead(ts.pickup_datetime) OVER (
                    PARTITION BY ta.shift_id ORDER BY ts.pickup_datetime
                ) - ts.dropoff_datetime > INTERVAL 25 MINUTE
    ),
    allev AS (
        SELECT * FROM bookend
        UNION ALL SELECT * FROM trip_events
        UNION ALL SELECT * FROM breaks
    )
    SELECT
        'EV-' || lpad((row_number() OVER (ORDER BY shift_id, event_ts, ord))::VARCHAR, 10, '0') AS event_id,
        shift_id, driver_id, vehicle_id,
        event_ts,
        status_code,
        zone_id,
        -- ~0.3% of events arrive with a clock skew of up to two minutes, which
        -- is enough to invert their order against the neighbouring event.
        CASE WHEN hb(shift_id || event_ts::VARCHAR) % 333 = 0
             THEN event_ts + INTERVAL 2 MINUTE ELSE event_ts END AS received_ts,
        CASE WHEN hb(shift_id) % 100 < 92 THEN 'tablet' ELSE 'driver_app' END AS source_system
    FROM allev
    """
)

con.execute(
    """
    CREATE OR REPLACE TABLE ops_raw.maintenance_event AS
    SELECT
        'MX-' || lpad((row_number() OVER (ORDER BY v.vehicle_id, n.d))::VARCHAR, 7, '0') AS maintenance_id,
        v.vehicle_id,
        DATE '2024-01-01' + INTERVAL ((hb(v.vehicle_id::VARCHAR || n.d::VARCHAR) % 180)) DAY AS started_date,
        1 + (hb(v.vehicle_id::VARCHAR || n.d::VARCHAR || 'dur') % 4)                        AS down_days,
        CASE n.d % 4 WHEN 0 THEN 'scheduled_service' WHEN 1 THEN 'brake_repair'
                     WHEN 2 THEN 'tlc_inspection'    ELSE 'collision_repair' END              AS maintenance_type,
        round(120 + (hb(v.vehicle_id::VARCHAR || n.d::VARCHAR || 'cost') % 2400), 2)        AS cost_usd
    FROM ops_raw.vehicle v
    CROSS JOIN (SELECT unnest([1, 2, 3]) AS d) n
    WHERE hb(v.vehicle_id::VARCHAR || n.d::VARCHAR || 'has') % 3 < 2
    """
)

for t in ("garage", "vehicle", "driver", "lease_agreement", "shift",
          "trip_assignment", "driver_status_event", "maintenance_event"):
    n = con.execute(f"SELECT count(*) FROM ops_raw.{t}").fetchone()[0]
    print(f"ops_raw.{t:24} {n:>12,}")

con.close()
