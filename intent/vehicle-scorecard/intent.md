---
kind: transformation
---

# Intent: Vehicle scorecard (per medallion, month by month)

Four durable artifacts carry a unit of work through the loop — `intent.md`, `design.md`, `plan.md`, `verify.md` — one per primitive, and each records only the approval that gates its own exit, so no file mirrors another. This file is the intent artifact: it fixes `kind:` above, one of the six in `lib/kinds/registry.json`, and records the intent approval that lets the loop advance into `design`.

## Goal
Depot managers want to compare vehicles the same way they already compare
drivers with `ops.mart_driver_scorecard` — a ranked scorecard — but per
medallion and broken out month by month, not summed over a single period.

## Source system
`gold` dbt marts/aggregates in this warehouse (`agg_vehicle_monthly`, `dim_vehicle`, `dim_garage`), the same layer `mart_driver_scorecard` and `mart_vehicle_utilisation` already read from.

## Target
`gold.ops` mart schema, alongside `mart_driver_scorecard` and `mart_vehicle_utilisation`.

## Objects in scope
- New mart: `mart_vehicle_scorecard`, one row per vehicle (medallion) per month, ranked

## Deliverables inventory

| # | Deliverable | Kind | Notes |
| --- | --- | --- | --- |
| 1 | Vehicle scorecard mart (per medallion, per month, ranked) | mart/model | Modeled on `mart_driver_scorecard`'s ranking approach, applied to vehicles at monthly grain instead of summed-over-period |

## Grain
**Decision.** One row per vehicle (medallion) per month — `vehicle_key` + `month_start_date`, unique key. Unlike `mart_driver_scorecard`, which sums each driver to one row over the whole reporting window, this mart keeps the month as part of the grain so depot managers can compare a vehicle month over month, per the request ("per medallion and month by month"). Built from `agg_vehicle_monthly`, which is already at this grain.

**Date scope — decision, resolved from profiling evidence.** Restricted to `CONTEXT.md`'s reporting window, 2024-01-01 to 2024-07-01 (Jan-Jun 2024). `agg_vehicle_monthly` also carries a partial Dec 2023 row for 105 of the 420 vehicles, reflecting a few hours of activity for the whole month (as low as 0.8 online hours) — an unfloored fleet-wide rank on revenue per online hour would let those rows distort the top of the table. Restricting to the reporting window drops them and leaves a uniform Jan-Jun 2024 set: 420 vehicles x 6 months, 2,520 rows, no partial months, `online_hours` ranging 423-650 per vehicle-month. See `data-slice.md` for the full profiling evidence.

## Consumers
**Fact**, from `transformation/models/marts/ops/_ops.yml`: the `garage_operations_review` exposure (dashboard, owner Fleet Operations, "Drives driver coaching and vehicle reallocation") already depends on `mart_driver_scorecard` and `mart_vehicle_utilisation` for the monthly depot review. This mart is a new dependency of that same exposure. Consumer: depot managers / Fleet Operations, monthly.

## Metric definitions
- **Ranking metric — decision.** Revenue per online hour, mirroring `mart_driver_scorecard`'s fairness rationale (gross revenue rewards whoever was scheduled the most hours, which is a dispatch fact, not a performance one). Already computed as `revenue_per_online_hour` in `agg_vehicle_monthly`.
- **Ranking floor — decision.** None. Every vehicle-month is ranked as-is; no low-sample-month flag (explicit departure from `mart_driver_scorecard`'s 40-hour floor).
- **Ranking scope — decision.** Fleet-wide rank only (`rank()` over all vehicle-months in the fleet). No garage-scoped rank, an explicit departure from `mart_driver_scorecard`, which computes both.
- Supporting metrics (`occupancy_rate`, `trips_per_online_hour`, etc.) — **fact**, already defined as business rules in `agg_vehicle_monthly` / `mart_vehicle_utilisation`; carried through unchanged.

## SLAs / freshness
**Fact**, from `CONTEXT.md`: no orchestration in this repo — the loader and `dbt build` run externally, nightly at 03:00 ET. This mart is picked up by that existing nightly build, same as `mart_driver_scorecard` and `mart_vehicle_utilisation`. Consumption cadence is monthly, per the depot review.

## Success criteria
- `mart_vehicle_scorecard` has exactly one row per `vehicle_key` per `month_start_date`.
- Each row carries a fleet-wide rank for that month, computed on revenue per online hour.
- Depot managers can pull the mart and compare vehicles across the fleet, month by month, the way `mart_driver_scorecard` already lets them compare drivers.

## Out of scope
- Garage-scoped ranking (fleet-wide rank only, by explicit decision).
- A ranking floor / low-sample-month flag (by explicit decision).
- Maintenance-cost-adjusted ranking, vehicle-attribute segmentation (fuel type, age), and multi-month trend/rank-history columns — kept a straight parallel to `mart_driver_scorecard`'s shape, not extended.
- Replacing or modifying `mart_vehicle_utilisation` — it stays as the period-summed asset-utilization view; this is a new, separate mart at a different grain and for a different purpose.
- A `## Schedule` or `## Semantic Model` design section — no orchestration or semantic layer exists in this repo today; the mart rides the existing external nightly build.

## Open questions
- None.

## Approvals

Append-only. `capturing-intent` — not a coordinator — appends `- [x] User approved intent — YYYY-MM-DD HH:MM (UTC)` only after a structured `AskUserQuestion` response whose first-option value was `approved`. Do not append from inference.

- [x] User approved intent — 2026-08-09 (UTC)
