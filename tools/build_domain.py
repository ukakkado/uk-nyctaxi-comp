"""Build the NYC TLC Domain Workspace (bronze -> silver -> gold) in DuckDB.

This stands in for a customer's existing brownfield warehouse. It is authored as
a plausible TLC analytics team would have authored it over time, WITHOUT
knowledge of any particular Intent. Conforming decisions here are the ordinary
ones a team makes; they are not tuned to make any later request easy or hard.

Layering contract:
  bronze  landed raw, source names and types preserved, ingestion metadata added
  silver  conformed: renamed, typed, unioned, deduped. Structure only --
          business rules (date windows, fare validity) are NOT applied here
  gold    business marts, where the filtering and aggregation rules live
"""

import glob
import os
import duckdb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw")
DB = os.path.join(ROOT, "domain.duckdb")

if os.path.exists(DB):
    os.remove(DB)
con = duckdb.connect(DB)

for s in ("bronze", "silver", "gold"):
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {s}")

# --------------------------------------------------------------------------
# BRONZE -- landed raw. Source column names/types preserved verbatim.
# Ingestion metadata mirrors what a dlt-style loader stamps on every row.
# --------------------------------------------------------------------------

def land(table, pattern, load_id):
    files = sorted(glob.glob(os.path.join(RAW, pattern)))
    assert files, pattern
    con.execute(
        f"""
        CREATE OR REPLACE TABLE bronze.{table} AS
        SELECT *,
               '{load_id}'                        AS _load_id,
               regexp_extract(filename, '[^/]+$') AS _source_file,
               TIMESTAMP '2024-07-02 03:14:00'    AS _loaded_at
        FROM read_parquet('{os.path.join(RAW, pattern)}', filename = true)
        """
    )


land("yellow_tripdata", "yellow_tripdata_2024-*.parquet", "load_2024h1_yellow")
land("green_tripdata", "green_tripdata_2024-*.parquet", "load_2024h1_green")

con.execute(
    f"""
    CREATE OR REPLACE TABLE bronze.taxi_zone_lookup AS
    SELECT LocationID, Borough, Zone, service_zone,
           'load_2024h1_ref'              AS _load_id,
           'taxi_zone_lookup.csv'         AS _source_file,
           TIMESTAMP '2024-07-02 03:14:00' AS _loaded_at
    FROM read_csv('{os.path.join(RAW, "taxi_zone_lookup.csv")}')
    """
)

# Hand-maintained reference tables. The team keeps these in the warehouse
# because the TLC data dictionary is a PDF and nobody wants to re-read it.
con.execute(
    """
    CREATE OR REPLACE TABLE bronze.payment_type_ref AS
    SELECT * FROM (VALUES
        (0, 'Flex Fare trip'), (1, 'Credit card'), (2, 'Cash'),
        (3, 'No charge'), (4, 'Dispute'), (5, 'Unknown'), (6, 'Voided trip')
    ) t(payment_type, payment_type_desc)
    """
)
con.execute(
    """
    CREATE OR REPLACE TABLE bronze.rate_code_ref AS
    SELECT * FROM (VALUES
        (1, 'Standard rate'), (2, 'JFK'), (3, 'Newark'),
        (4, 'Nassau or Westchester'), (5, 'Negotiated fare'), (6, 'Group ride')
    ) t(rate_code_id, rate_code_desc)
    """
)
con.execute(
    """
    CREATE OR REPLACE TABLE bronze.vendor_ref AS
    SELECT * FROM (VALUES
        (1, 'Creative Mobile Technologies'), (2, 'Curb Mobility'),
        (6, 'Myle Technologies'), (7, 'Helix')
    ) t(vendor_id, vendor_name)
    """
)

# --------------------------------------------------------------------------
# SILVER -- conformed. Yellow and green are unioned onto one grain so that
# downstream marts do not have to know which fleet a trip came from.
#
# Conforming note (the ordinary decision): columns that exist on only one of
# the two fleets are dropped rather than carried as a mostly-null column.
# Yellow's Airport_fee and green's ehail_fee/trip_type do not survive into
# silver. Anything needing them reads bronze.
# --------------------------------------------------------------------------

con.execute(
    """
    CREATE OR REPLACE TABLE silver.trips AS
    WITH unioned AS (
        SELECT 'yellow'                AS service_type,
               VendorID                AS vendor_id,
               tpep_pickup_datetime    AS pickup_datetime,
               tpep_dropoff_datetime   AS dropoff_datetime,
               passenger_count,
               trip_distance,
               RatecodeID              AS rate_code_id,
               store_and_fwd_flag,
               PULocationID            AS pickup_location_id,
               DOLocationID            AS dropoff_location_id,
               payment_type,
               fare_amount, extra, mta_tax, tip_amount, tolls_amount,
               improvement_surcharge, congestion_surcharge, total_amount,
               _load_id, _source_file
        FROM bronze.yellow_tripdata
        UNION ALL
        SELECT 'green'                 AS service_type,
               VendorID                AS vendor_id,
               lpep_pickup_datetime    AS pickup_datetime,
               lpep_dropoff_datetime   AS dropoff_datetime,
               passenger_count,
               trip_distance,
               RatecodeID              AS rate_code_id,
               store_and_fwd_flag,
               PULocationID            AS pickup_location_id,
               DOLocationID            AS dropoff_location_id,
               payment_type,
               fare_amount, extra, mta_tax, tip_amount, tolls_amount,
               improvement_surcharge, congestion_surcharge, total_amount,
               _load_id, _source_file
        FROM bronze.green_tripdata
    ),
    keyed AS (
        SELECT md5(concat_ws('|', service_type, vendor_id,
                             pickup_datetime, dropoff_datetime,
                             pickup_location_id, dropoff_location_id,
                             trip_distance, total_amount)) AS trip_key,
               *,
               row_number() OVER (
                   PARTITION BY service_type, vendor_id, pickup_datetime,
                                dropoff_datetime, pickup_location_id,
                                dropoff_location_id, trip_distance, total_amount
                   ORDER BY _source_file
               ) AS _dup_rank
        FROM unioned
    )
    SELECT * EXCLUDE (_dup_rank) FROM keyed WHERE _dup_rank = 1
    """
)

con.execute(
    """
    CREATE OR REPLACE TABLE silver.zones AS
    SELECT LocationID   AS location_id,
           Borough      AS borough,
           Zone         AS zone_name,
           service_zone
    FROM bronze.taxi_zone_lookup
    """
)
con.execute(
    """
    CREATE OR REPLACE TABLE silver.payment_types AS
    SELECT payment_type, payment_type_desc FROM bronze.payment_type_ref
    """
)
con.execute(
    """
    CREATE OR REPLACE TABLE silver.rate_codes AS
    SELECT rate_code_id, rate_code_desc FROM bronze.rate_code_ref
    """
)

# --------------------------------------------------------------------------
# GOLD -- the marts that already exist. Business rules live here: the reporting
# window, and the "billable trip" definition the finance team agreed on.
# --------------------------------------------------------------------------

con.execute(
    """
    CREATE OR REPLACE TABLE gold.dim_zone AS
    SELECT z.location_id,
           z.borough,
           z.zone_name,
           z.service_zone,
           z.borough IN ('Unknown', 'N/A') AS is_unknown_borough
    FROM silver.zones z
    """
)

con.execute(
    """
    CREATE OR REPLACE TABLE gold.mart_daily_zone_revenue AS
    SELECT CAST(t.pickup_datetime AS DATE) AS trip_date,
           t.pickup_location_id,
           z.borough,
           z.zone_name,
           count(*)              AS trip_count,
           sum(t.fare_amount)    AS fare_revenue,
           sum(t.tip_amount)     AS tip_revenue,
           sum(t.total_amount)   AS total_revenue
    FROM silver.trips t
    LEFT JOIN gold.dim_zone z ON t.pickup_location_id = z.location_id
    WHERE t.pickup_datetime >= TIMESTAMP '2024-01-01'
      AND t.pickup_datetime <  TIMESTAMP '2024-07-01'
      AND t.total_amount > 0
    GROUP BY 1, 2, 3, 4
    """
)

con.execute(
    """
    CREATE OR REPLACE TABLE gold.mart_monthly_service_summary AS
    SELECT date_trunc('month', t.pickup_datetime) AS trip_month,
           t.service_type,
           p.payment_type_desc,
           count(*)                 AS trip_count,
           sum(t.trip_distance)     AS total_miles,
           sum(t.total_amount)      AS total_revenue,
           avg(t.total_amount)      AS avg_fare
    FROM silver.trips t
    LEFT JOIN silver.payment_types p ON t.payment_type = p.payment_type
    WHERE t.pickup_datetime >= TIMESTAMP '2024-01-01'
      AND t.pickup_datetime <  TIMESTAMP '2024-07-01'
      AND t.total_amount > 0
    GROUP BY 1, 2, 3
    """
)

rows = con.execute(
    """
    SELECT schema_name, table_name, estimated_size
    FROM duckdb_tables() ORDER BY schema_name, table_name
    """
).fetchall()
for r in rows:
    print(f"{r[0]:8} {r[1]:32} {r[2]:>12,}")
con.close()
print("\nDB:", DB, f"{os.path.getsize(DB)/1e9:.2f} GB")
