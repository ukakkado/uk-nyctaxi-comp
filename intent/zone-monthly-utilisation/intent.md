---
kind: transformation
---

# Intent: Zone-by-month utilisation (R10)

This file is the intent artifact: it fixes `kind:` above and records the intent approval that lets the loop advance into `design`.

## Goal
See, per zone per month, how much of the fleet's time is spent sitting versus
actually earning there — the "utilisation" question already answered
per-vehicle (`mart_vehicle_utilisation`) and per-zone-per-hour
(`agg_zone_occupancy_hourly`), but not yet per zone per month.

## Source system
`agg.agg_zone_occupancy_hourly` — the level directly below the target grain —
**not** `core.fct_status_interval` directly.

**Decision.** Built from `agg_zone_occupancy_hourly` because every measure it
carries (`total_hours`, `on_trip_hours`, `available_hours`, `break_hours`) is
a plain sum that rolls up cleanly to the month, and `zone_occupancy_rate` is
already this codebase's convention to recompute from summed parts, not
re-average. Rebuilding from the 3.77M-row status-interval fact again would
just recompute numbers the hourly aggregate already got right — the same
pyramid principle `agg_driver_daily` → `agg_driver_monthly` already follows.

## Target
`gold.ops` — `mart_zone_utilisation`, matching `mart_vehicle_utilisation`'s
naming and schema convention (an "at rest vs earning" utilisation mart for a
different dimension).

## Objects in scope
- New mart, zone x month grain

## Deliverables inventory

| # | Deliverable | Kind | Notes |
| --- | --- | --- | --- |
| 1 | `mart_zone_utilisation` | mart/model | Built from `agg_zone_occupancy_hourly`, rolled to zone x month |

## Grain
**Decision.** One row per zone per `month_start_date` — see Open questions
for the zone-key choice.

## Consumers
**Decision (assumed).** Depot managers / Fleet Operations, per the request's
own framing and consistent with `garage_operations_review`'s existing
driver/vehicle-reallocation purpose. Not yet named in that exposure's
`depends_on` — flagged for design-time wiring.

## Metric definitions
**Fact.** `zone_occupancy_rate` is already defined on
`agg_zone_occupancy_hourly` as `on_trip_hours / total_hours`. Rolled up by
summing `on_trip_hours` and `total_hours` across the month first, then
dividing — not by averaging the hourly rate.

## SLAs / freshness
**Fact**: nightly external build; monthly consumption cadence, matching
`garage_operations_review`'s cadence.

## Success criteria
- `mart_zone_utilisation` has one row per zone per month.
- Occupancy/available/break hours sum correctly from
  `agg_zone_occupancy_hourly` for a spot-checked zone-month.
- Depot managers can compare zones the way `mart_vehicle_utilisation` already
  lets them compare vehicles.

## Out of scope
- Zone x hour-of-day detail (`agg_zone_occupancy_hourly` continues to serve
  that).
- Any ranking (this is a utilisation mart, not a scorecard, matching
  `mart_vehicle_utilisation`'s own shape).
- Maintenance-driven availability adjustment — `mart_vehicle_utilisation`'s
  `available_days` concept has no zone analog (a zone doesn't go "out of
  service" the way a vehicle does), so it isn't carried over.

## Open questions
- Key on `zone_natural_key` (stable, unversioned) or `zone_key` (versioned
  surrogate)? `agg_zone_occupancy_hourly` itself already exposes
  `zone_natural_key`, `zone_name`, and `borough_name` directly rather than
  `zone_key` — following that precedent, `zone_natural_key` is the
  recommended default, but it affects how this mart joins back to `dim_zone`
  downstream, so it's recorded as open rather than silently decided.

## Approvals

Append-only. `capturing-intent` — not a coordinator — appends `- [x] User approved intent — YYYY-MM-DD HH:MM (UTC)` only after a structured `AskUserQuestion` response whose first-option value was `approved`. Do not append from inference.
