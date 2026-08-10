---
kind: transformation
---

# Intent: Driver-week aggregate (R7)

This file is the intent artifact: it fixes `kind:` above and records the intent approval that lets the loop advance into `design`.

## Goal
The shift-bidding cycle is weekly, but the driver pyramid only goes day
(`agg_driver_daily`) and month (`agg_driver_monthly`) — Ops keeps deriving the
weekly number by hand. Build `agg_driver_weekly` to stop that.

## Source system
`agg.agg_driver_daily` — the level directly below the target grain, plus
`core.dim_date` for the week boundary.

## Target
`gold.agg` — `agg_driver_weekly`, next to `agg_driver_daily` /
`agg_driver_monthly`.

## Objects in scope
- New agg model, driver x week grain

## Deliverables inventory

| # | Deliverable | Kind | Notes |
| --- | --- | --- | --- |
| 1 | `agg_driver_weekly` | mart/model | Built from `agg_driver_daily`, same pyramid convention as day → month |

## Grain
**Decision.** One row per `driver_key` per `week_start_date`.

Week boundary — **fact**: `dim_date.week_start_date` (`date_trunc('week',
calendar_date)`) is already the warehouse's one definition of a week. Reused
here rather than inventing a second one; joined via `agg_driver_daily.shift_date
= dim_date.calendar_date`.

## Consumers
**Decision (assumed).** Operations / shift-bidding coordinators. No existing
exposure names a weekly driver consumer (`garage_operations_review` is
monthly) — the request names a business process, not a system of record, so
this is flagged as an assumption rather than a fact.

## Metric definitions
**Fact.** Every rate (`occupancy_rate`, `revenue_per_online_hour`,
`revenue_per_trip`) is already defined on `agg_driver_daily` as
summed-numerator-over-summed-denominator. The weekly rollup recomputes them
the same way rather than averaging the daily rates — the explicit convention
`agg_driver_daily`'s own comment states ("rates cannot be averaged up").

## SLAs / freshness
**Fact**: nightly external build; weekly shift-bidding consumption cadence
(stated in the request).

## Success criteria
- `agg_driver_weekly` has one row per `driver_key` per `week_start_date`.
- Every measure sums correctly from `agg_driver_daily`, and every rate is
  recomputed from summed parts.
- Ops reads the weekly number directly instead of deriving it by hand.

## Out of scope
- **Decision.** No explicit partial-week flag. Weeks straddling the edges of
  the reporting window (first week of January, last week of June) include
  only the in-window days present in `agg_driver_daily` — mirroring
  `agg_driver_monthly`, which doesn't flag partial months either.
- Any ranking/scorecard behavior (`mart_driver_scorecard`'s job, at a
  different grain).
- Garage- or fleet-level rollups (`agg_garage_monthly` already exists).

## Open questions
- None.

## Approvals

Append-only. `capturing-intent` — not a coordinator — appends `- [x] User approved intent — YYYY-MM-DD HH:MM (UTC)` only after a structured `AskUserQuestion` response whose first-option value was `approved`. Do not append from inference.
