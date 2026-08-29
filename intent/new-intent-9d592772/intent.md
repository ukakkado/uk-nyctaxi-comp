---
kinds: [transformation]
---

# Intent: Zone by Month Utilisation

This file fixes the ordered work kinds, deliverables, atomic acceptance units, and approval that let the work advance into design.

## Goal

Fleet Operations needs to see, for each zone in each month, how much of the time our cars spend physically present in that zone is spent actually earning (on a trip) versus sitting idle or on break. This tells them which zones are productive versus which are dead time, so they can reposition fleet and negotiate garage contracts with evidence.

## Source system

Fleet operations status stream, already landed as `fct_status_interval` (one row per driver-vehicle state interval, carrying `zone_key`, `status_code` ∈ {ON_TRIP, AVAILABLE, DISPATCHED, BREAK, LOGIN, LOGOUT}, and `interval_seconds`). Supplemented by `dim_zone` for zone attributes.

## Target

DuckDB-local ephemeral workspace, dbt `agg` layer under `transformation/models/marts/agg/`.

## Objects in scope

- `agg_zone_utilisation_monthly` — new aggregate model at zone × month grain

## Deliverables inventory

| # | Deliverable | Kind | Notes |
| --- | --- | --- | --- |
| 1 | `agg_zone_utilisation_monthly` | model | Zone × month utilisation aggregate. All vehicles in status stream (not fleet-filtered). |

## Success criteria

- The model produces one row per (zone, month) combination within the reporting window
- Utilisation rate is computable as earning hours / total hours in zone, with raw hour components also exposed
- Every zone in `dim_zone` (excluding unresolved zones) appears for every month it has any status interval data
- The model builds cleanly in the sandbox and passes unit tests

## Acceptance units

| ID | Requirement | Source | Resolution | Evidence needed |
| --- | --- | --- | --- | --- |
| A-01 | Grain is one row per (zone, month). Unique key is (zone_key, month_start_date). | user request | supplied decision | `dbt test` unique + not_null on composite key |
| A-02 | Source population is `fct_status_interval` joined to `dim_zone` (current version only). | derived fact | derived fact | Model SQL inspection; row count ≤ sum of intervals in source |
| A-03 | `total_hours` = sum of all `interval_seconds` / 3600 for the zone-month. | user request ("time our cars sit in a zone") | supplied decision | Independent SUM from `fct_status_interval` grouped by zone and month |
| A-04 | `earning_hours` = sum of `interval_seconds` where `status_code = 'ON_TRIP'` / 3600. | user request ("actually earning there") | supplied decision | Independent SUM with ON_TRIP filter from source |
| A-05 | `utilisation_rate` = `earning_hours` / `total_hours`, null when `total_hours` = 0. | user request | supplied decision | Independent recomputation from raw hours |
| A-06 | Unresolved zones (`is_unresolved_zone = true`) are excluded from the output. | workspace convention (CONTEXT.md: zone ids 264/265 pollute rollups) | derived fact | No rows with `is_unresolved_zone = true` in output |
| A-07 | Model exposes raw hour components alongside the ratio: `total_hours`, `earning_hours` (ON_TRIP), `idle_hours` (AVAILABLE), `break_hours` (BREAK), plus `utilisation_rate`. DISPATCHED, LOGIN, LOGOUT intervals count toward `total_hours` but are not named buckets — matches `agg_zone_occupancy_hourly` convention. | workspace convention (`agg_zone_occupancy_hourly` exposes the same pattern) | derived fact | Column presence check |
| A-08 | "Our cars" scope — all vehicles in the status stream, not filtered to fleet-attributed only. Matches `agg_zone_occupancy_hourly` which also uses all intervals. | user request ("our cars") + workspace convention | derived fact (default: all vehicles) | Row count = count of all intervals in source grouped by zone-month |
| A-09 | Month is derived from `interval_date`, truncated to first of month. Output column is `month_start_date`. | workspace convention | derived fact | Distinct month values match expected reporting window |

## Out of scope

- Changes to `fct_status_interval` or `dim_zone` (upstream sources are not modified)
- Orchestration or scheduling changes (existing nightly build covers this)
- Semantic layer / MetricFlow definitions (not requested)
- Zone-level daily or hourly granularity (existing `agg_zone_occupancy_hourly` covers hourly)
- Revenue metrics (existing `mart_daily_zone_revenue` covers revenue)

## Open questions

- None

## Approvals

Append-only. `capturing-intent` — not a coordinator — appends `- [x] User approved intent — YYYY-MM-DD HH:MM (UTC)` only after a structured `AskUserQuestion` response whose first-option value was `approved`. Do not append from inference.
