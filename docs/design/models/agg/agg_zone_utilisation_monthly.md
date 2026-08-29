---
artifacts: [agg_zone_utilisation_monthly]
---

# `agg_zone_utilisation_monthly`

## Grain

One row per (zone, month): the unique key is `(zone_key, month_start_date)`. A row represents all status intervals for that zone in that calendar month, aggregated into hour buckets by status code.

## Decisions

- **Layer: `agg`.** Follows the existing `agg_zone_occupancy_hourly` pattern — an aggregate over `fct_status_interval` at a coarser grain than the hourly fact. No intermediate model needed; the aggregation is a single GROUP BY. [A-01, A-02]

- **Materialization: table.** Consistent with all other `agg` models in the project. The output is ~1,305 rows — trivially materializable and cheap to rebuild.

- **Source: `fct_status_interval` directly, not `agg_zone_occupancy_hourly`.** The hourly aggregate would require re-aggregation across hour boundaries and loses no precision for this use case, but going directly from the interval fact is simpler and avoids an unnecessary dependency. The hourly model serves a different purpose (locating idle time by hour); this model serves a different purpose (monthly zone productivity). [A-02]

- **Status code handling: ON_TRIP = earning, AVAILABLE = idle, BREAK = break. DISPATCHED, LOGIN, LOGOUT count toward `total_hours` but have no named bucket.** The bucketing logic matches `agg_zone_occupancy_hourly`'s convention; column names differ (`earning_hours` vs `on_trip_hours`, `idle_hours` vs `available_hours`, `utilisation_rate` vs `zone_occupancy_rate`) per intent mandate. DISPATCHED means en route to a pickup — the driver is present but not yet earning. LOGIN/LOGOUT are session transitions with negligible duration. `utilisation_rate` uses the `safe_divide` macro for null-on-zero consistency with other agg models. [A-03, A-04, A-05, A-07]

- **Zone filter: exclude `is_unresolved_zone = true`.** Zone ids 264 (Unknown) and 265 (N/A) are real rows in the lookup but pollute rollups. Consistent with CONTEXT.md convention. Note: `agg_zone_occupancy_hourly` does NOT filter these — this model explicitly excludes them per A-06. [A-06]

- **Vehicle scope: all vehicles, not fleet-filtered.** `fct_status_interval` carries intervals for every vehicle in the status stream. Filtering to fleet-attributed only would reduce coverage and diverge from `agg_zone_occupancy_hourly`'s convention. The model measures zone productivity for all traffic, not just our fleet. [A-08]

- **Month derivation: `date_trunc('month', interval_date)` → `month_start_date`.** Standard calendar month truncation. [A-09]

## Rejected

- **Using `agg_zone_occupancy_hourly` as source.** Rejected because it adds an unnecessary dependency and the re-aggregation from hourly to monthly is no simpler than aggregating from the interval fact directly. The hourly model's purpose (locating idle time by hour) is different from this model's purpose (monthly zone productivity).

- **Fleet-only filter.** Rejected because it would reduce coverage, diverge from the existing zone occupancy pattern, and the user's "our cars" is naturally read as "all cars we observe in the status stream" rather than "only fleet-attributed vehicles."

- **Separate intermediate model.** Rejected because the aggregation is a single GROUP BY with no complex logic that would benefit from an intermediate step. YAGNI.

## Rerun behaviour

Idempotent. A second run produces identical output for the same input. The model is a full-scan aggregation (not incremental) — it reads all intervals and groups by zone-month. Safe to backfill or refresh at any time.

## Consumers

- Fleet Operations — the garage operations review (per CONTEXT.md, alongside `mart_vehicle_utilisation` and `agg_garage_monthly`)
- Ad-hoc analysis of zone productivity trends

## Gotchas

- `interval_seconds = 0` exists for LOGOUT intervals. SUM handles this naturally (adds zero), but consumers should know that `total_hours` includes these zero-duration intervals.
- DISPATCHED time is in the denominator (`total_hours`) but not in any named bucket. The sum of `earning_hours + idle_hours + break_hours` will not equal `total_hours`. This is intentional and matches `agg_zone_occupancy_hourly`.

## History

- `new-intent-9d592772`, 2026-08-29: Initial creation — zone × month utilisation aggregate.
