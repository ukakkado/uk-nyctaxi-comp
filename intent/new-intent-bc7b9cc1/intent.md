kinds: [transformation]
---

# Intent: Zone by month utilisation

This file fixes the ordered work kinds, deliverables, atomic acceptance units, and approval that let the work advance into design.

## Goal

Fleet Operations needs to see, for each zone and month, how much of the time cars present in that zone were actually earning (on a trip) versus sitting idle or waiting. This answers the question: "Which zones hold our cars without paying them back?" — a question the existing hourly occupancy model cannot answer at the monthly granularity the operations review needs.

## Source system

dbt-managed models sourced from `ops_raw.driver_status_event` via `intermediate.int_status_intervals` and `core.fct_status_interval`, joined to `core.dim_zone` for zone attributes. No new external source connections.

## Target

DuckDB-local, `agg` schema. New model: `agg_zone_utilisation_monthly`.

## Objects in scope

- `agg_zone_utilisation_monthly` — new aggregate model at zone × month grain

## Deliverables inventory

| # | Deliverable | Kind | Notes |
| --- | --- | --- | --- |
| 1 | `agg_zone_utilisation_monthly` | model | Zone × month utilisation: time earning vs. time present. Sources from `fct_status_interval` + `dim_zone`. |

## Success criteria

- Fleet Operations can query one table to see, per zone per month, total hours present, hours earning (ON_TRIP), hours idle (AVAILABLE + DISPATCHED), hours on break, and the utilisation rate (earning / present).
- The model is consistent with `agg_zone_occupancy_hourly` — rolling up the hourly model's hours to month must match the monthly model's hours within rounding.
- Zones with no status intervals in a month produce no row (no zero-filled gaps).

## Acceptance units

| ID | Requirement | Source | Resolution | Evidence needed |
| --- | --- | --- | --- | --- |
| A-01 | Model relation is `agg.agg_zone_utilisation_monthly` | user request + workspace convention (agg schema for zone aggregates) | derived fact | `dbt show --select agg_zone_utilisation_monthly` returns rows from `agg` schema |
| A-02 | Grain is one row per (zone_natural_key, month). Month is derived from `interval_date` truncated to month. | user request ("zone by month") | supplied decision | `count(*) = count(distinct zone_natural_key \|\| '-' \|\| month)` — no duplicate keys |
| A-03 | `total_hours` = sum of `interval_seconds / 3600.0` across all status intervals in the zone-month. | derived from `agg_zone_occupancy_hourly` convention | derived fact | `sum(total_hours)` matches `sum(total_hours)` from `agg_zone_occupancy_hourly` grouped to month |
| A-04 | `on_trip_hours` = sum of `interval_seconds / 3600.0` where `status_code = 'ON_TRIP'`. | user request ("actually earning there") + existing convention in `agg_zone_occupancy_hourly` | supplied decision | Independent recomputation from `fct_status_interval` where `status_code = 'ON_TRIP'` |
| A-05 | `idle_hours` = sum of `interval_seconds / 3600.0` where `status_code in ('AVAILABLE', 'DISPATCHED')`. | user request ("sit in a zone") + existing convention in `int_shift_occupancy` | derived fact | Independent recomputation from `fct_status_interval` where `status_code in ('AVAILABLE','DISPATCHED')` |
| A-06 | `break_hours` = sum of `interval_seconds / 3600.0` where `status_code = 'BREAK'`. | derived from `agg_zone_occupancy_hourly` convention | derived fact | Independent recomputation from `fct_status_interval` where `status_code = 'BREAK'` |
| A-07 | `utilisation_rate` = `on_trip_hours / nullif(total_hours, 0)`. | user request ("how much of the time... earning") | derived fact | `utilisation_rate = on_trip_hours / total_hours` for every row where `total_hours > 0` |
| A-08 | Zone attributes carried: `zone_natural_key`, `zone_name`, `borough_name`, `is_airport_zone`. | workspace convention (zone attributes in `agg_zone_occupancy_hourly`) | derived fact | Columns present in output schema |
| A-09 | Source population: all rows in `fct_status_interval` joined to `dim_zone` on `zone_key`, within the report window. | workspace convention (`in_report_window` macro) | derived fact | Row count matches `fct_status_interval` join coverage |
| A-10 | Zones with no intervals in a month produce no row. | workspace convention (no zero-fill in existing aggregates) | derived fact | No rows where `total_hours = 0` |
| A-11 | `distinct_vehicles` = count of distinct `vehicle_key` with any interval in the zone-month. | derived from `agg_zone_occupancy_hourly` convention | derived fact | Matches `count(distinct vehicle_key)` from `fct_status_interval` grouped to zone-month |
| A-12 | `distinct_drivers` = count of distinct `driver_key` with any interval in the zone-month. | derived from `agg_zone_occupancy_hourly` convention | derived fact | Matches `count(distinct driver_key)` from `fct_status_interval` grouped to zone-month |

## Out of scope

- Changes to `agg_zone_occupancy_hourly` or any existing model.
- Vehicle-level or driver-level utilisation breakdowns (those belong to `mart_vehicle_utilisation` and `agg_driver_monthly`).
- Trip-based revenue or fare metrics (those belong to `agg_trip_zone_daily` and finance marts).
- Orchestration or scheduling changes.
- Semantic layer / MetricFlow definitions.

## Open questions

- None — all material branches resolved from workspace conventions and the existing `agg_zone_occupancy_hourly` model pattern.

## Approvals

- [x] User approved intent — 2026-08-29 13:08 (UTC)
