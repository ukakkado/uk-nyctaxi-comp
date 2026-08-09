"""Build the master-data platform's raw landing schema (`mdm_raw`).

The operator runs a small MDM platform that owns reference data for the whole
business. It takes the bare TLC code lists -- which are little more than a code
and a label -- and enriches them with the attributes the business actually
reasons about: settlement terms on a payment method, flat-fare amounts on a rate
plan, geography and points of interest on a zone, contract terms on a vendor.

Two of these tables are versioned at source, with `valid_from` / `valid_to` and
a natural key, because the real-world things they describe change:
  * `zone_master`     -- TLC re-designates zones (natural key: location_id)
  * `vendor_master`   -- technology vendors are renamed and acquired
                         (natural key: vendor_id)

Everything lands raw: source column names, source types, ingestion metadata.
Conforming and SCD2 assembly happen in dbt, not here.
"""

import os
import duckdb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "domain.duckdb")

con = duckdb.connect(DB)
con.execute("CREATE OR REPLACE MACRO hb(x) AS CAST(hash(x) % 100000000 AS BIGINT)")
con.execute("CREATE SCHEMA IF NOT EXISTS mdm_raw")

LOADED = "TIMESTAMP '2024-07-02 02:40:00'"

# ---------------------------------------------------------------------------
# ZONE MASTER -- versioned. Enriches the 265 TLC zones with geography, a
# congestion-zone flag, and a demand tier. A handful of zones carry a second
# version because TLC re-designated them mid-history.
# ---------------------------------------------------------------------------
con.execute(
    f"""
    CREATE OR REPLACE TABLE mdm_raw.zone_master AS
    WITH base AS (
        SELECT
            z.LocationID                                  AS location_id,
            z.Borough                                     AS borough_name,
            z.Zone                                        AS zone_label,
            z.service_zone                                AS tlc_service_zone,
            -- Deterministic pseudo-geography, stable per zone.
            round(40.55 + (hb(z.Zone::VARCHAR) % 42000) / 100000.0, 6)      AS centroid_lat,
            round(-74.05 + (hb(z.Zone::VARCHAR || 'lon') % 38000) / 100000.0, 6) AS centroid_lon,
            round(0.4 + (hb(z.Zone::VARCHAR || 'area') % 850) / 100.0, 3)   AS area_sq_mi,
            (hb(z.Zone::VARCHAR || 'pop') % 92000) + 1800                   AS resident_population,
            z.LocationID IN (1, 132, 138)                                     AS is_airport_zone,
            -- The Manhattan congestion-relief zone is south of 96th Street.
            (z.Borough = 'Manhattan' AND hb(z.Zone::VARCHAR || 'cz') % 100 < 62) AS is_congestion_zone,
            CASE WHEN z.LocationID IN (1, 132, 138) THEN 'airport'
                 WHEN z.Borough = 'Manhattan'       THEN 'core'
                 WHEN z.Borough IN ('Unknown','N/A') THEN 'unresolved'
                 ELSE 'boro' END                                              AS zone_class,
            CASE (hb(z.Zone::VARCHAR || 'tier') % 4)
                 WHEN 0 THEN 'very_high' WHEN 1 THEN 'high'
                 WHEN 2 THEN 'moderate'  ELSE 'low' END                       AS demand_tier
        FROM bronze.taxi_zone_lookup z
    ),
    versioned AS (
        -- Current version for every zone.
        SELECT *, DATE '2019-01-01' AS valid_from_date,
                  DATE '2099-12-31' AS valid_to_date,
                  1 AS source_version
        FROM base
        WHERE location_id % 37 <> 0

        UNION ALL

        -- Zones that were re-designated: an expired first version...
        SELECT * EXCLUDE (demand_tier),
               CASE demand_tier WHEN 'very_high' THEN 'high'
                                WHEN 'high' THEN 'moderate' ELSE 'low' END,
               DATE '2019-01-01', DATE '2023-09-01', 1
        FROM base WHERE location_id % 37 = 0

        UNION ALL

        -- ...and the version that replaced it.
        SELECT *, DATE '2023-09-01', DATE '2099-12-31', 2
        FROM base WHERE location_id % 37 = 0
    )
    SELECT *,
           'mdm_zone_v3'    AS _load_id,
           'zone_master.csv' AS _source_file,
           {LOADED}          AS _loaded_at
    FROM versioned
    """
)

# ---------------------------------------------------------------------------
# VENDOR MASTER -- versioned. VendorID 2 traded as VeriFone until the Curb
# Mobility rebrand; the contract tier changed at the same time.
# ---------------------------------------------------------------------------
con.execute(
    f"""
    CREATE OR REPLACE TABLE mdm_raw.vendor_master AS
    SELECT * , 'mdm_vendor_v2' AS _load_id, 'vendor_master.csv' AS _source_file, {LOADED} AS _loaded_at
    FROM (VALUES
        (1, 'Creative Mobile Technologies LLC', 'CMT',  'gold',     DATE '2011-01-01', DATE '2099-12-31', 1, true),
        (2, 'VeriFone Inc',                     'VTS',  'silver',   DATE '2011-01-01', DATE '2023-07-01', 1, true),
        (2, 'Curb Mobility LLC',                'CURB', 'gold',     DATE '2023-07-01', DATE '2099-12-31', 2, true),
        (6, 'Myle Technologies Inc',            'MYLE', 'bronze',   DATE '2022-03-01', DATE '2099-12-31', 1, true),
        (7, 'Helix Technologies',               'HELIX','bronze',   DATE '2021-06-01', DATE '2023-01-15', 1, false)
    ) t(vendor_id, vendor_legal_name, vendor_short_code, contract_tier,
        valid_from_date, valid_to_date, source_version, is_approved)
    """
)

# ---------------------------------------------------------------------------
# Non-versioned reference masters.
# ---------------------------------------------------------------------------
con.execute(
    f"""
    CREATE OR REPLACE TABLE mdm_raw.payment_method_master AS
    SELECT *, 'mdm_pay_v1' AS _load_id, 'payment_method_master.csv' AS _source_file, {LOADED} AS _loaded_at
    FROM (VALUES
        (0, 'Flex Fare trip', 'electronic', true,  1, 0.0250, true),
        (1, 'Credit card',    'electronic', true,  2, 0.0290, true),
        (2, 'Cash',           'cash',       false, 0, 0.0000, true),
        (3, 'No charge',      'waived',     false, 0, 0.0000, false),
        (4, 'Dispute',        'contested',  false, 30, 0.0000, false),
        (5, 'Unknown',        'unknown',    false, 0, 0.0000, false),
        (6, 'Voided trip',    'voided',     false, 0, 0.0000, false)
    ) t(payment_type_code, payment_method_name, settlement_class,
        tip_is_captured, settlement_days, processor_fee_pct, counts_as_revenue)
    """
)

con.execute(
    f"""
    CREATE OR REPLACE TABLE mdm_raw.rate_plan_master AS
    SELECT *, 'mdm_rate_v1' AS _load_id, 'rate_plan_master.csv' AS _source_file, {LOADED} AS _loaded_at
    FROM (VALUES
        (1,  'Standard metered',      false, NULL,  false, true,  'meter'),
        (2,  'JFK flat fare',         true,  70.00, true,  true,  'flat'),
        (3,  'Newark',                false, NULL,  true,  true,  'meter_plus'),
        (4,  'Nassau or Westchester', false, NULL,  false, true,  'meter_plus'),
        (5,  'Negotiated fare',       false, NULL,  false, false, 'negotiated'),
        (6,  'Group ride',            true,  NULL,  false, false, 'flat'),
        (99, 'Undocumented code',     false, NULL,  false, false, 'unknown')
    ) t(rate_code, rate_plan_name, is_flat_fare, flat_fare_amount,
        is_airport_plan, is_metered_baseline, pricing_model)
    """
)

con.execute(
    f"""
    CREATE OR REPLACE TABLE mdm_raw.fare_regime_master AS
    SELECT *, 'mdm_regime_v1' AS _load_id, 'fare_regime_master.csv' AS _source_file, {LOADED} AS _loaded_at
    FROM (VALUES
        ('IMP-2015',  'improvement_surcharge', 0.30, 'all',    DATE '2015-01-01', DATE '2023-12-01'),
        ('IMP-2023',  'improvement_surcharge', 1.00, 'all',    DATE '2023-12-01', DATE '2099-12-31'),
        ('MTA-2009',  'mta_tax',               0.50, 'all',    DATE '2009-11-01', DATE '2099-12-31'),
        ('CON-2019Y', 'congestion_surcharge',  2.50, 'yellow', DATE '2019-02-01', DATE '2099-12-31'),
        ('CON-2019G', 'congestion_surcharge',  2.75, 'green',  DATE '2019-02-01', DATE '2099-12-31'),
        ('APT-2022',  'airport_access_fee',    1.25, 'yellow', DATE '2022-09-01', DATE '2023-12-01'),
        ('APT-2023',  'airport_access_fee',    1.75, 'yellow', DATE '2023-12-01', DATE '2099-12-31')
    ) t(regime_code, fare_component, rate_amount, applies_to_fleet,
        valid_from_date, valid_to_date)
    """
)

con.execute(
    f"""
    CREATE OR REPLACE TABLE mdm_raw.borough_master AS
    SELECT *, 'mdm_boro_v1' AS _load_id, 'borough_master.csv' AS _source_file, {LOADED} AS _loaded_at
    FROM (VALUES
        ('Manhattan',     'MN', 'Manhattan Core', 1694251, 22.83, true,  true),
        ('Brooklyn',      'BK', 'Outer Boroughs', 2736074, 69.50, true,  false),
        ('Queens',        'QN', 'Outer Boroughs', 2405464, 108.10, true, false),
        ('Bronx',         'BX', 'Outer Boroughs', 1472654, 42.10, true,  false),
        ('Staten Island', 'SI', 'Outer Boroughs',  495747, 58.37, true,  false),
        ('EWR',           'NJ', 'Out of State',         0,  0.00, false, false),
        ('Unknown',       'XX', 'Unresolved',           0,  0.00, false, false),
        ('N/A',           'XX', 'Unresolved',           0,  0.00, false, false)
    ) t(borough_name, borough_code, reporting_region, resident_population,
        area_sq_mi, is_nyc, is_core_market)
    """
)

# ---------------------------------------------------------------------------
# ZONE POINTS OF INTEREST -- a genuine many-to-many. One zone holds several
# points of interest and one category spans many zones, so the dimensional
# model needs a bridge rather than a flattened column.
# ---------------------------------------------------------------------------
con.execute(
    f"""
    CREATE OR REPLACE TABLE mdm_raw.zone_poi AS
    WITH cats AS (
        SELECT * FROM (VALUES
            ('AIRPORT','Airport terminal',5), ('RAIL','Rail terminal',5),
            ('SUBWAY','Subway interchange',2), ('STADIUM','Stadium or arena',4),
            ('HOSPITAL','Hospital',3), ('UNIVERSITY','University campus',3),
            ('HOTEL','Hotel cluster',4), ('NIGHTLIFE','Nightlife district',4),
            ('PARK','Major park',1), ('FERRY','Ferry terminal',3)
        ) c(poi_category, poi_category_name, demand_weight)
    ),
    z AS (SELECT LocationID AS location_id, Zone AS zone_label FROM bronze.taxi_zone_lookup)
    SELECT
        'POI-' || lpad((row_number() OVER (ORDER BY z.location_id, c.poi_category))::VARCHAR, 5, '0') AS poi_id,
        z.location_id,
        c.poi_category,
        c.poi_category_name,
        c.demand_weight,
        z.zone_label || ' ' || c.poi_category_name AS poi_name,
        'mdm_poi_v1' AS _load_id, 'zone_poi.csv' AS _source_file, {LOADED} AS _loaded_at
    FROM z CROSS JOIN cats c
    WHERE (z.location_id IN (1, 132, 138) AND c.poi_category = 'AIRPORT')
       OR (hb(z.zone_label || c.poi_category) % 100 < 11 AND c.poi_category <> 'AIRPORT')
    """
)

# ---------------------------------------------------------------------------
# CALENDAR MASTER -- real US federal holidays plus NYC-specific demand events.
# ---------------------------------------------------------------------------
con.execute(
    f"""
    CREATE OR REPLACE TABLE mdm_raw.calendar_master AS
    WITH d AS (
        SELECT unnest(generate_series(DATE '2023-12-01', DATE '2024-12-31', INTERVAL 1 DAY))::DATE AS calendar_date
    ),
    hol AS (
        SELECT * FROM (VALUES
            (DATE '2024-01-01','New Year''s Day','federal'),
            (DATE '2024-01-15','Martin Luther King Jr. Day','federal'),
            (DATE '2024-02-19','Presidents'' Day','federal'),
            (DATE '2024-03-17','St Patrick''s Day Parade','city_event'),
            (DATE '2024-04-08','Solar eclipse','city_event'),
            (DATE '2024-05-27','Memorial Day','federal'),
            (DATE '2024-06-19','Juneteenth','federal'),
            (DATE '2024-07-04','Independence Day','federal'),
            (DATE '2024-09-02','Labor Day','federal'),
            (DATE '2024-11-28','Thanksgiving Day','federal'),
            (DATE '2024-12-25','Christmas Day','federal')
        ) h(holiday_date, holiday_name, holiday_class)
    )
    SELECT
        d.calendar_date,
        h.holiday_name,
        h.holiday_class,
        (h.holiday_date IS NOT NULL)                          AS is_holiday,
        dayofweek(d.calendar_date) IN (0, 6)                  AS is_weekend,
        -- NYC public schools run roughly September to late June.
        (month(d.calendar_date) BETWEEN 1 AND 6
         OR month(d.calendar_date) BETWEEN 9 AND 12)          AS is_school_term,
        'mdm_cal_v1' AS _load_id, 'calendar_master.csv' AS _source_file, {LOADED} AS _loaded_at
    FROM d LEFT JOIN hol h ON h.holiday_date = d.calendar_date
    """
)

# ---------------------------------------------------------------------------
# WEATHER -- daily observation per borough. A real demand driver: rain lifts
# short-hop demand and snow suppresses everything.
# ---------------------------------------------------------------------------
con.execute(
    f"""
    CREATE OR REPLACE TABLE mdm_raw.weather_daily AS
    WITH d AS (
        SELECT unnest(generate_series(DATE '2024-01-01', DATE '2024-06-30', INTERVAL 1 DAY))::DATE AS obs_date
    ),
    b AS (SELECT unnest(['Manhattan','Brooklyn','Queens','Bronx','Staten Island','EWR']) AS borough_name)
    SELECT
        'WX-' || strftime(d.obs_date, '%Y%m%d') || '-' || replace(b.borough_name, ' ', '') AS observation_id,
        d.obs_date,
        b.borough_name,
        -- Seasonal curve through the first half of the year, plus local noise.
        round(34 + 26 * sin((dayofyear(d.obs_date) - 100) * 3.14159 / 182.0)
              + (hb(d.obs_date::VARCHAR || b.borough_name) % 900) / 100.0, 1) AS temp_avg_f,
        round(greatest(0, (hb(d.obs_date::VARCHAR || b.borough_name || 'p') % 100 - 68)) / 22.0, 2) AS precip_inches,
        CASE WHEN month(d.obs_date) IN (1, 2)
                  AND hb(d.obs_date::VARCHAR || b.borough_name || 's') % 100 > 88
             THEN round((hb(d.obs_date::VARCHAR || 'sn') % 700) / 100.0, 1) ELSE 0.0 END AS snow_inches,
        round(3 + (hb(d.obs_date::VARCHAR || b.borough_name || 'w') % 1800) / 100.0, 1)  AS wind_mph,
        'mdm_wx_v1' AS _load_id, 'weather_daily.csv' AS _source_file, {LOADED} AS _loaded_at
    FROM d CROSS JOIN b
    """
)

for t in ("zone_master", "vendor_master", "payment_method_master", "rate_plan_master",
          "fare_regime_master", "borough_master", "zone_poi", "calendar_master",
          "weather_daily"):
    n = con.execute(f"SELECT count(*) FROM mdm_raw.{t}").fetchone()[0]
    print(f"mdm_raw.{t:24} {n:>10,}")

con.close()
