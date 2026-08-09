# NYC Taxi Analytics — Domain Context

Analytics warehouse for the TLC trip record data. Owned by the Data Platform
team; consumed by Finance and by the Operations reporting group.

## Layers

| Layer | Contents | Owner |
| --- | --- | --- |
| `bronze` | Landed TLC parquet, verbatim. Source column names and types preserved; only `_load_id` / `_source_file` / `_loaded_at` added. | ingestion |
| `silver` | Conformed. Yellow and green unioned onto one trip grain with shared names. | platform |
| `gold` | dbt-managed marts. Business rules live here. | platform |

Only `gold` is dbt-managed. `bronze` and `silver` are declared to dbt as
sources and are produced by the loader outside this repo.

## Ubiquitous language

- **Trip** — one completed taxi journey. Grain of `silver.trips`, keyed by
  `trip_key`.
- **Fleet / service type** — `yellow` (medallion) or `green` (boro taxi).
  Green may not pick up passengers in the Manhattan core or at the airports
  except by pre-arrangement, so airport volume is overwhelmingly yellow.
- **Zone** — one of 265 TLC `LocationID` values. Every trip carries a pickup
  and a dropoff zone; TLC never emits a null or unknown-to-the-lookup id.
- **Billable trip** — the finance definition used by every mart in `gold`:
  `total_amount > 0` within the reporting window. Trips failing this are
  refunds, voids, and meter errors.
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

- Finance — `mart_daily_zone_revenue` (daily, in the Monday revenue pack).
- Operations reporting — `mart_monthly_service_summary` (monthly).

No semantic layer. No orchestration in this repo; the loader and `dbt build`
are scheduled externally, nightly at 03:00 ET.
