---
kinds: [transformation]
---

# Intent: Garage-by-week utilisation

This file is the intent artifact: it fixes `kinds:` above — an ordered list
covering every artifact family the objective needs, per the composition
contract in `_shared/playbooks/kinds/README.md` — and records the intent
approval that lets the loop advance into `design`.

## Goal
Depot managers already compare vehicles (`mart_vehicle_utilisation`) and
zones (`mart_zone_utilisation`) on an "at rest vs earning" basis. They want
the same comparison per garage, but by week rather than by the month
`agg_garage_monthly` already reports at — a faster-reacting number for the
weekly depot cadence, the way `agg_driver_weekly` was built to stop a
by-hand weekly derivation Ops was doing for drivers.

## Source system
`agg.agg_vehicle_daily` — the level directly below the target grain — joined
to `core.dim_garage`, plus `core.fct_maintenance` for downtime and
`core.dim_date` for the week boundary. **Not** `agg.agg_garage_monthly`; a
weekly grain cannot be rolled down from a monthly one.

**Decision.** `agg_garage_monthly` itself is built by joining
`agg_vehicle_monthly` + `dim_garage` and grouping by month + garage. No
garage-day aggregate exists, so this mart repeats that same construction one
level down: `agg_vehicle_daily` + `dim_garage`, grouped by week + garage.
`agg_vehicle_daily` does not carry maintenance downtime the way
`agg_vehicle_monthly` does (that netting happens only at the monthly grain,
via a separate `fct_maintenance` join) — so `down_days` and
`maintenance_cost` are sourced directly from `core.fct_maintenance`, bucketed
by week from `started_date`, mirroring `agg_vehicle_monthly`'s own
`downtime` CTE pattern but at week grain instead of month.

`core.dim_date.week_start_date` (`date_trunc('week', calendar_date)`) is
reused as the one week boundary already established for
`agg_driver_weekly`, joined via `agg_vehicle_daily.shift_date =
dim_date.calendar_date`.

## Target
`gold.ops` — `mart_garage_utilisation`, matching `mart_vehicle_utilisation`
and `mart_zone_utilisation`'s home and naming convention (an "at rest vs
earning" utilisation mart, this time for the garage dimension).

## Objects in scope
- New mart, garage x week grain

## Deliverables inventory

| # | Deliverable | Kind | Notes |
| --- | --- | --- | --- |
| 1 | `mart_garage_utilisation` | mart/model | Built from `agg_vehicle_daily` + `dim_garage` + `fct_maintenance`, rolled to garage x week |

## Grain
**Decision.** One row per `garage_key` per `week_start_date`. Kept as a
per-week row rather than summed over the whole reporting window, matching
`mart_zone_utilisation`'s (not `mart_vehicle_utilisation`'s) precedent of
keeping the period unit in the grain, since the request explicitly asks to
compare garages "by week", not once over the whole window.

## Consumers
**Decision (assumed).** Depot managers / Fleet Operations, per the request's
own framing. The `garage_operations_review` exposure (`_ops.yml`) already
depends on `mart_vehicle_utilisation` and `agg_garage_monthly` for the
*monthly* depot review, but it names no weekly garage consumer — same gap
`agg_driver_weekly` hit for a weekly driver consumer. Flagged as an
assumption, not a fact, and for design-time wiring into that exposure (or a
new one) rather than assumed silently.

## Metric definitions
**Fact.** Every measure already has a business-rule definition on
`agg_garage_monthly`, carried over unchanged at week grain instead of month:
`active_vehicles` (distinct vehicles), `shift_count`, `trip_count`,
`online_hours`, `on_trip_hours`, `gross_revenue`, `maintenance_cost`,
`down_days`, `occupancy_rate` (`on_trip_hours / online_hours`, summed parts
divided, never averaged), `revenue_per_online_hour`, and
`bay_occupancy_rate` (`active_vehicles / bay_capacity`).

## SLAs / freshness
**Fact**, from `CONTEXT.md`: no orchestration in this repo — the loader and
`dbt build` run externally, nightly at 03:00 ET. This mart rides that same
external nightly build. Consumption cadence is weekly, per the request.

## Success criteria
- `mart_garage_utilisation` has exactly one row per `garage_key` per
  `week_start_date`.
- Every measure sums correctly from `agg_vehicle_daily` / `fct_maintenance`
  for a spot-checked garage-week, and every rate is recomputed from summed
  parts, never averaged.
- Depot managers can compare garages week over week the way
  `mart_vehicle_utilisation` and `mart_zone_utilisation` already let them
  compare vehicles and zones.

## Out of scope
- A new `agg_garage_weekly` aggregate as a separate layer below the mart —
  matching how `mart_vehicle_utilisation` and `mart_zone_utilisation` are
  themselves built directly from the level below, with no intermediate agg
  model created solely to feed the mart.
- Garage-day grain (R14's ask, a separate, unbuilt request; this intent is
  weekly only).
- Any ranking or scorecard behavior (`mart_driver_scorecard`'s and the
  vehicle-scorecard intent's job, not this mart's, matching
  `mart_vehicle_utilisation`'s and `mart_zone_utilisation`'s own precedent of
  staying a utilisation view rather than a ranked one).
- An availability-adjusted rate (`agg_vehicle_monthly`'s
  `availability_adjusted_activity_rate` concept) — not carried over, matching
  `agg_garage_monthly`'s own precedent of publishing raw `down_days` /
  `maintenance_cost` without a derived availability rate.
- Replacing or modifying `agg_garage_monthly` — it stays the monthly garage
  view; this is a new, separate mart at a different grain.
- An `## Orchestration` or `## Semantic Model` design section — no
  orchestration or semantic layer exists in this repo today; the mart rides
  the existing external nightly build.

## Open questions
- None.

## Approvals

Append-only. `capturing-intent` — not a coordinator — appends `- [x] User
approved intent — YYYY-MM-DD HH:MM (UTC)` only after a structured
`AskUserQuestion` response whose first-option value was `approved`. Do not
append from inference.
