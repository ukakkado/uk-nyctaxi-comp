---
artifacts: [agg_zone_monthly]
---

# `agg_zone_monthly`

Zone × month utilization: how much of the time vehicles spend in each zone is earning (ON_TRIP) versus idle. The monthly counterpart to `agg_zone_occupancy_hourly`, matching the cadence of `agg_vehicle_monthly`, `agg_driver_monthly`, and `agg_garage_monthly` for the Fleet Operations review.

## Grain

One row per `(zone_natural_key, month_start_date)`. `month_start_date` is `date_trunc('month', interval_date)`.

## Columns

**Grain and zone attributes** (from `agg_zone_occupancy_hourly`, which carries them from `dim_zone`):
- `month_start_date` — first day of month
- `zone_natural_key` — TLC LocationID
- `zone_name`, `borough_name`, `is_airport_zone` — zone attributes

**Hour measures** (rolled up from `agg_zone_occupancy_hourly`):
- `total_hours` — all interval hours in the zone (all statuses)
- `on_trip_hours` — status_code = 'ON_TRIP'
- `available_hours` — status_code = 'AVAILABLE'
- `break_hours` — status_code = 'BREAK'
- `other_hours` — residual: `total_hours - on_trip_hours - available_hours - break_hours` (captures DISPATCHED, LOGIN, LOGOUT)

**Distinct counts** (computed from `fct_status_interval` directly):
- `distinct_drivers` — count(distinct driver_key)
- `distinct_vehicles` — count(distinct vehicle_key)

**Rate:**
- `zone_utilization_rate` — `on_trip_hours / total_hours` (null when total_hours = 0)

## Decisions

- **Hybrid source for hours vs. distinct counts.** Hours (total, on_trip, available, break) roll up from `agg_zone_occupancy_hourly` so the monthly totals reconcile with the hourly model row-for-row (A-03 through A-07, A-14). Distinct driver and vehicle counts compute from `fct_status_interval` directly, because `count(distinct)` cannot be re-aggregated from pre-aggregated hourly values — summing hourly distinct counts would overcount, averaging would undercount (A-09, A-10). **See [ADR 0003](../../../adr/0003-hybrid-source-for-monthly-distinct-counts.md).**
- **Join strategy for the hybrid approach.** The two branches (hourly rollup and distinct-count computation) join on `(zone_natural_key, month_start_date)` using an INNER JOIN. The distinct-count branch applies the same zone filter as the hourly model: `fct_status_interval` uses a LEFT JOIN to `dim_zone` with `is_current_version = true`, so intervals with null `zone_key` (non-current or unresolved zones) are excluded. This ensures the zone set matches the hourly branch (A-11).
- **`other_hours` column captures the status gap.** The hourly model buckets only ON_TRIP, AVAILABLE, and BREAK. The fact table also carries DISPATCHED, LOGIN, and LOGOUT intervals, which contribute to `total_hours` but sit outside the three named buckets. `other_hours = total_hours - on_trip_hours - available_hours - break_hours` makes the gap explicit rather than hiding it (A-07).
- **Utilization rate = on_trip_hours / total_hours.** Matches the hourly model's `zone_occupancy_rate` logic. Null when total_hours is zero, using `safe_divide`. This is "of the time vehicles are physically present in the zone, what fraction are earning" — not a fleet-capacity denominator (A-08). **Column naming:** The hourly model uses `zone_occupancy_rate`; the monthly model uses `zone_utilization_rate`. The name change is intentional: "occupancy" at hourly grain describes the fraction of time vehicles are on-trip vs. idle in a given hour; "utilization" at monthly grain describes the same ratio but over a longer period, and the term "utilization" aligns with the request (R10) and with `mart_vehicle_utilisation`. The calculation is identical; the name reflects the grain and the business question.
- **All zones included, no unresolved-zone filter.** Follows the existing convention in `agg_zone_occupancy_hourly` and `agg_trip_zone_daily`. `dim_zone.is_unresolved_zone` is available for consumers to filter. Filtering here would diverge from the hourly model and make reconciliation harder (A-11).
- **Reporting window applied.** `interval_date >= report_start and < report_end`, consistent with other agg models. July 2024 has only 3 rows in the hourly source (boundary effect), so the monthly row for July will reflect partial data — this is expected and correct (A-12).

## Rejected

- **Building entirely from `fct_status_interval`.** Would duplicate the hourly model's zone join, daypart mapping, and status bucketing logic, and risk divergence between hourly and monthly numbers. The pyramid pattern (each level built from the one below) prevents this.
- **Rolling distinct counts up from `agg_zone_occupancy_hourly`.** The hourly model carries `distinct_drivers` and `distinct_vehicles` as pre-aggregated counts. Summing these across hours overcounts (the same driver appears in multiple hours); averaging undercounts. The only correct approach is to re-aggregate from the fact table.
- **Filtering unresolved zones (264 Unknown, 265 N/A).** Would make this model inconsistent with the hourly model and with `agg_trip_zone_daily`. Consumers who need to exclude unresolved zones can filter on `dim_zone.is_unresolved_zone`.

## Rerun behaviour

Full refresh. The model is a complete rollup of the hourly aggregate within the reporting window. A second run produces identical output given the same inputs. No incremental logic, no late-arriving backfill — the reporting window is fixed by `report_start` / `report_end` vars, and changing them is a conscious decision that changes the numbers.

## Consumers

Fleet Operations monthly review, alongside `agg_vehicle_monthly`, `agg_driver_monthly`, and `agg_garage_monthly`. No exposure or semantic model yet.

## Gotchas

- **July 2024 is partial.** The reporting window ends 2024-07-01, so July has only 3 rows in the hourly source. The monthly row for July will show very low hours. This is correct — the window boundary is intentional, not a data gap.
- **`other_hours` is not zero.** DISPATCHED, LOGIN, and LOGOUT intervals contribute ~3,800 hours total. A reader expecting `total_hours = on_trip_hours + available_hours + break_hours` will see a gap. The `other_hours` column makes this explicit.

## History

- `zone-monthly-utilization`, 2026-08-31: Initial creation — zone × month utilization aggregate.
