# NYC Taxi Analytics — Domain Context

> **Before trusting any number here, read [docs/data-provenance.md](docs/data-provenance.md).**
> This warehouse mixes real TLC open data with two invented source systems.
> Every dollar is real; every person is not.

Analytics warehouse for TLC trip-record data. Owned by the Data Platform team;
consumed by Finance Reporting, Commercial, Fleet Operations, and Data Platform.

## Layers

| Layer | Contents | Owner |
| --- | --- | --- |
| `bronze` | Landed TLC Parquet, verbatim. Source column names and types are preserved; only `_load_id`, `_source_file`, and `_loaded_at` are added. | ingestion |
| `silver` | Conformed TLC data. Yellow and Green are unioned to one trip grain with shared names. | platform |
| `ops_raw` | Generated fleet operations: garages, vehicles, drivers, leases, shifts, assignments, status events, and maintenance. | operations source builder |
| `mdm_raw` | Generated and maintained master data: zones, vendors, payment methods, rate plans, calendar, POIs, and weather. | master-data source builder |
| `staging` | dbt views that shape the four source layers for downstream use. | platform |
| `intermediate` | dbt tables for trip enrichment, fare components, data-quality flags, status intervals, and shift calculations. | platform |
| `core`, `agg`, `finance`, `ops` | dbt dimensions, facts, aggregates, and consumer-facing marts. Business rules are applied at the model that needs them. | platform |

`bronze`, `silver`, `ops_raw`, and `mdm_raw` are dbt sources produced outside
dbt. dbt manages the `staging`, `intermediate`, `core`, `agg`, `finance`, and
`ops` model layers.

## Ubiquitous language

- **Trip** — one completed taxi journey. Grain of `silver.trips`, keyed by
  `trip_key`.
- **Fleet / service type** — `yellow` (medallion) or `green` (boro taxi).
  Green may not pick up passengers in the Manhattan core or at the airports
  except by pre-arrangement, so airport volume is overwhelmingly yellow.
- **Zone** — one of 265 TLC `LocationID` values. The current loaded data has a
  non-null, lookup-resolved pickup and dropoff zone for every trip.
- **Billable trip** — `total_amount > 0` within the reporting window. Finance
  revenue marts and selected aggregates opt into this definition. `core.fct_trip`
  retains all trips and exposes `is_billable`, so data-quality and operational
  models can analyse refunds, voids, and meter errors.
- **Reporting window** — 2024-01-01 to 2024-07-01, set by `report_start` /
  `report_end` vars. Not a sampling control; changing it changes the numbers
  Finance sees.

## Known data characteristics

- `payment_type` 3 (No charge) and 4 (Dispute) rows carry a fare but usually a
  zero tip. Any tip-rate metric that does not exclude them reads low.
- `total_amount` goes negative on refunds. `trip_distance` is 0 on a
  meaningful number of trips (meter started and stopped at the same place).
- Zone ids 264 (`Unknown`) and 265 (`N/A`) are real rows in the lookup, so
  they join cleanly and silently pollute any borough rollup. `dim_zone`
  carries `is_unknown_borough` for this reason; not every mart uses it.
- Tips are only recorded for card payments. Cash tips are not captured at all,
  so tip totals are structurally understated and cash trips are not "zero tip",
  they are unmeasured.

## Consumers

- Finance Reporting — the Monday revenue pack, backed by
  `finance.mart_daily_zone_revenue` and `finance.mart_revenue_component_bridge`.
- Commercial — the concession-negotiation pack, backed by
  `finance.mart_monthly_service_summary`.
- Fleet Operations — the garage operations review, backed by
  `ops.mart_driver_scorecard`, `ops.mart_vehicle_utilisation`, and
  `agg.agg_garage_monthly`.
- Data Platform — the data-quality review, backed by
  `ops.mart_trip_quality_scorecard`.

The aggregate models also support ad-hoc analysis; they are not all bound to a
declared exposure.

No semantic layer. No orchestration in this repo; the loader and `dbt build`
are scheduled externally, nightly at 03:00 ET.
