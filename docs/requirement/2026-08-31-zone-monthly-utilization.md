---
kinds: [transformation]
---

# Intent: Zone by Month Utilization

This file fixes the ordered work kinds, deliverables, atomic acceptance units, and approval that let the work advance into design.

## Goal

Fleet Operations needs to see how much of the time vehicles spend in each zone is actually earning (on-trip) versus idle (available, on-break). The existing `agg_zone_occupancy_hourly` provides this at hourly grain, but the operations review runs monthly and needs the same view rolled up to match the cadence of `agg_vehicle_monthly`, `agg_driver_monthly`, and `agg_garage_monthly`.

## Source system

Fleet operations status intervals (`ops_raw.status_intervals`), via `core.fct_status_interval` and `agg.agg_zone_occupancy_hourly`. Zone dimension from `core.dim_zone`.

**Hybrid approach:** Hours (total, on_trip, available, break) roll up from `agg_zone_occupancy_hourly` to ensure reconciliation with the hourly model. Distinct counts (drivers, vehicles) compute from `fct_status_interval` directly, because distinct counts cannot be safely re-aggregated from pre-aggregated hourly values.

## Target

DuckDB-local ephemeral workspace, `agg` schema, model `agg_zone_monthly`.

## Objects in scope

- `agg.agg_zone_monthly` — new dbt table at zone × month grain

## Deliverables inventory

| # | Deliverable | Kind | Notes |
| --- | --- | --- | --- |
| 1 | `agg.agg_zone_monthly` | mart/model | Zone × month utilization aggregate, built from `agg_zone_occupancy_hourly` |

## Success criteria

- One row per zone per month within the reporting window
- Utilization rate = on_trip_hours / total_hours, matching the hourly model's `zone_occupancy_rate` logic
- Component hours (total, on_trip, available, break) sum correctly and reconcile with the hourly aggregate
- Distinct vehicle and driver counts are present
- Model builds cleanly with `dbt build` and passes project evaluator

## Acceptance units

| ID | Requirement | Source | Resolution | Evidence needed |
| --- | --- | --- | --- | --- |
| A-01 | Grain is zone × month: one row per (zone_natural_key, month_start_date) combination | user request | supplied decision | `select zone_natural_key, month_start_date, count(*) from agg_zone_monthly group by 1,2 having count(*) > 1` returns zero rows |
| A-02 | month_start_date is the first day of the month (date_trunc to month) | derived fact | derived fact | `select distinct month_start_date from agg_zone_monthly` returns only first-of-month dates |
| A-03 | total_hours = sum of all interval hours in the zone for the month (all statuses) | user request "sit in a zone" | supplied decision | `select sum(total_hours) from agg_zone_monthly` matches `select sum(interval_seconds)/3600 from fct_status_interval` for the same zone-month |
| A-04 | on_trip_hours = sum of interval hours where status_code = 'ON_TRIP' | user request "actually earning there" | supplied decision | `select sum(on_trip_hours) from agg_zone_monthly` matches `select sum(interval_seconds)/3600 from fct_status_interval where status_code='ON_TRIP'` for the same zone-month |
| A-05 | available_hours = sum of interval hours where status_code = 'AVAILABLE' | derived from hourly model pattern | derived fact | `select sum(available_hours) from agg_zone_monthly` matches `select sum(interval_seconds)/3600 from fct_status_interval where status_code='AVAILABLE'` for the same zone-month |
| A-06 | break_hours = sum of interval hours where status_code = 'BREAK' | derived from hourly model pattern | derived fact | `select sum(break_hours) from agg_zone_monthly` matches `select sum(interval_seconds)/3600 from fct_status_interval where status_code='BREAK'` for the same zone-month |
| A-07 | other_hours = total_hours - on_trip_hours - available_hours - break_hours (captures DISPATCHED, LOGIN, LOGOUT status time) | derived fact from profiling | derived fact | `select other_hours, total_hours - on_trip_hours - available_hours - break_hours from agg_zone_monthly` shows matching values |
| A-08 | zone_utilization_rate = on_trip_hours / total_hours (null when total_hours = 0) | user request | supplied decision | `select zone_utilization_rate, on_trip_hours/total_hours from agg_zone_monthly where total_hours > 0` shows matching values |
| A-09 | distinct_vehicles = count of distinct vehicle_key in the zone for the month | derived from hourly model pattern | derived fact | `select distinct_vehicles from agg_zone_monthly` matches `select count(distinct vehicle_key) from fct_status_interval` for the same zone-month |
| A-10 | distinct_drivers = count of distinct driver_key in the zone for the month | derived from hourly model pattern | derived fact | `select distinct_drivers from agg_zone_monthly` matches `select count(distinct driver_key) from fct_status_interval` for the same zone-month |
| A-11 | Zone dimension joined on zone_natural_key with is_current_version = true | workspace convention | derived fact | All rows in agg_zone_monthly have matching dim_zone rows with is_current_version = true |
| A-12 | Reporting window filter applied: interval_date >= report_start and < report_end | workspace convention | derived fact | `select min(month_start_date), max(month_start_date) from agg_zone_monthly` falls within [report_start, report_end) |
| A-13 | Model materialized as table in agg schema | workspace convention | derived fact | `dbt run --select agg_zone_monthly` succeeds; `show tables from agg` includes agg_zone_monthly |
| A-14 | Monthly totals reconcile with hourly: sum(agg_zone_monthly.total_hours) = sum(agg_zone_occupancy_hourly.total_hours) for each zone-month | derived fact | derived fact | Join and compare; difference < 0.01h |

## Out of scope

- Trip-based revenue metrics (covered by `agg_trip_zone_daily`)
- Sub-monthly grain (covered by `agg_zone_occupancy_hourly`)
- Vehicle-level or driver-level detail (covered by `agg_vehicle_monthly`, `agg_driver_monthly`)
- Unresolved zone filtering (dim_zone.is_unresolved_zone available for consumers)
- Orchestration or semantic model artifacts

## Open questions

None

## Approvals

- [x] User approved intent — 2026-08-31 08:57 (UTC)
- [x] Design approved — 2026-08-31 09:02 (UTC) — design-reviewer APPROVE verdict

