# `agg_zone_utilisation_monthly`

## Purpose and interface

Zone-level monthly utilisation: how much of the time cars present in a zone were actually earning (on a trip) versus sitting idle, waiting, or on break. One row per (zone, month). Answers the Fleet Operations question: "Which zones hold our cars without paying them back?"

## Decisions

- **Source from `fct_status_interval` directly, not by rolling up `agg_zone_occupancy_hourly`.** The hourly model carries `total_hours`, `on_trip_hours`, `available_hours`, and `break_hours`, but does not separate `DISPATCHED` from `AVAILABLE`. The monthly model needs `idle_hours = AVAILABLE + DISPATCHED` as a distinct metric, which requires going back to the status-level fact. See [ADR 0003](../../../adr/0003-source-status-based-aggregates-from-interval-fact.md). (A-03, A-04, A-05)

- **Denominator is total interval time in the zone, including BREAK.** Alternative considered: net utilisation excluding break time from the denominator. Rejected: the user asked for "how much of the time cars sit in a zone vs. earning" — total presence is the contract. Break time is a real component of zone presence and belongs in the denominator; consumers who want a net measure can compute it from the exposed `break_hours`. See [ADR 0004](../../../adr/0004-utilisation-rate-denominator-is-total-presence.md). (A-07)

- **LOGIN and LOGOUT intervals are excluded by the join, not by a filter.** These statuses carry null `zone_key` (they occur before zone assignment or after zone release). The inner join to `dim_zone` on `zone_key` excludes them naturally. AVAILABLE intervals with null `zone_key` (pre-zone-assignment) are similarly excluded. This is a data characteristic, not a design choice — but it means the model's population is the 189,904 zone-resolved intervals, not the full 337,069. (A-09, A-10)

- **Zone resolution uses `is_current_version`.** Consistent with `agg_zone_occupancy_hourly` and `fct_status_interval`. A zone that changed version during the reporting window is resolved to its current attributes. (A-08)

- **Report window applied via `in_report_window` macro.** Consistent with trip-based aggregates (`agg_trip_zone_daily`, `agg_trip_zone_daypart_dow`). Note: `agg_zone_occupancy_hourly` does not apply the report window; this model does, matching the convention for consumer-facing monthly aggregates. (A-09)

- **No zero-fill.** Zones with no intervals in a month produce no row. Consistent with `agg_zone_occupancy_hourly` and `agg_trip_zone_daily`. (A-10)

## Output columns

| Column | Type | Description |
| --- | --- | --- |
| `month` | date | First day of the month (date_trunc to month) |
| `zone_natural_key` | integer | TLC LocationID |
| `zone_name` | varchar | Zone display name |
| `borough_name` | varchar | Borough name |
| `is_airport_zone` | boolean | Airport zone flag |
| `total_hours` | double | All interval time in zone (hours) |
| `on_trip_hours` | double | ON_TRIP interval time (hours) |
| `idle_hours` | double | AVAILABLE + DISPATCHED interval time (hours) |
| `break_hours` | double | BREAK interval time (hours) |
| `utilisation_rate` | double | on_trip_hours / total_hours |
| `distinct_vehicles` | integer | Count of distinct vehicles with any interval |
| `distinct_drivers` | integer | Count of distinct drivers with any interval |

## Boundaries and guardrails

This aggregate owns zone-month utilisation from the status stream. It does not own trip-based revenue (that is `agg_trip_zone_daily`), vehicle-level utilisation (that is `mart_vehicle_utilisation`), or driver-level metrics (that is `agg_driver_monthly`).

The row-count contract: `sum(total_hours)` in this model must equal `sum(total_hours)` from `agg_zone_occupancy_hourly` grouped to month, within floating-point rounding. This is the consistency check with the hourly model.

## Change impact

**Additive only.** No existing models are modified. No downstream consumers exist yet — this is a new leaf in the DAG. The model depends on `fct_status_interval` and `dim_zone`, both of which are unchanged.

## Consumers

Fleet Operations — the garage operations review. Joins with `dim_zone` attributes for zone-level reporting.

## References

- [Intent](../../../intent/new-intent-bc7b9cc1/intent.md)
- [Data slice](../../requirements/slice-new-intent-bc7b9cc1.md)
- [ADR 0003 — Source status-based aggregates from interval fact](../../../adr/0003-source-status-based-aggregates-from-interval-fact.md)
- [ADR 0004 — Utilisation rate denominator is total presence](../../../adr/0004-utilisation-rate-denominator-is-total-presence.md)
- [Hourly occupancy model](../../../../transformation/models/marts/agg/agg_zone_occupancy_hourly.sql)
- [Status interval fact](../../../../transformation/models/marts/core/fct_status_interval.sql)
