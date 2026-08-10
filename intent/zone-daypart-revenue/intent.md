---
kind: transformation
---

# Intent: Retire mart_daily_zone_revenue for zone-by-daypart grain (R12)

This file is the intent artifact: it fixes `kind:` above and records the intent approval that lets the loop advance into `design`.

## Goal
Retire `mart_daily_zone_revenue` — nobody looks at the isolated daily number
— and replace it with the same revenue breakdown at zone x daypart grain
instead of zone x day.

## Source system
`core.fct_trip` + `core.dim_zone` + `core.dim_daypart` — **not**
`agg_trip_zone_daypart_dow`, despite it already existing at a related grain.

**Decision.** `agg_trip_zone_daypart_dow` is zone x daypart x day-of-week x
fleet, and critically doesn't pre-apply the billable filter as a row-level
gate the way `mart_daily_zone_revenue` does (ADR 0002) — it carries
`billable_trip_count` alongside `trip_count` for all rows, revenue inclusive
of non-billable trips. Finance's replacement mart needs the ADR 0002 filter
applied the same way the retiring mart applies it, so it's built fresh from
`fct_trip` rather than wrapping the existing agg model.

## Target
`gold.finance` — new `mart_zone_daypart_revenue`, replacing
`mart_daily_zone_revenue` in that schema.

## Objects in scope
- Retire `mart_daily_zone_revenue`
- New `mart_zone_daypart_revenue`

## Deliverables inventory

| # | Deliverable | Kind | Notes |
| --- | --- | --- | --- |
| 1 | Retire `mart_daily_zone_revenue` | mart/model | Repoint `monday_revenue_pack`'s `depends_on` to the new mart first — nothing should depend on the retiring one when it's dropped |
| 2 | New `mart_zone_daypart_revenue` | mart/model | Same column shape as the retiring mart (trip_count, fare/tip/surcharge/toll/total revenue), grouped by zone x daypart instead of zone x date |

## Grain
**Decision.** One row per (`pickup_location_id`, `daypart_code`) — daypart
alone, no date and no day-of-week, per the request's literal wording
("zone-by-daypart grain") and its own stated reason (nobody isolates a single
day already). This collapses the whole reporting window into each row, the
same way `agg_od_flow_matrix` collapses zone pairs — flagged below as worth
confirming, since it's a bigger grain change than "daily → still-by-date but
bucketed by daypart" might have implied.

## Consumers
**Fact.** `monday_revenue_pack` exposure (Finance Reporting), currently
depending on `mart_daily_zone_revenue` + `mart_revenue_component_bridge` —
must be repointed to the new mart as part of deliverable 1, not left
dangling.

## Metric definitions
**Fact**, identical to the retiring mart: `trip_count`, `fare_revenue`,
`tip_revenue`, `surcharge_revenue` (via `total_surcharges` macro),
`toll_revenue`, `total_revenue` — same columns, coarser grain.

Billable filter — **fact**, inherited unchanged: `is_billable` +
`in_report_window`, ADR 0002, applied in gold exactly as the retiring mart
already does.

Zone key — **decision**: group by `zone_natural_key`, matching
`mart_daily_zone_revenue`'s own existing choice over the versioned `zone_key`.

## SLAs / freshness
**Fact**: same nightly external build; weekly Monday-pack consumption
cadence (`CONTEXT.md`, `monday_revenue_pack` exposure).

## Success criteria
- `mart_zone_daypart_revenue` has one row per pickup zone x daypart, covering
  the same reporting window and billable rule as the retiring mart.
- `monday_revenue_pack`'s `depends_on` no longer references
  `mart_daily_zone_revenue`.
- Every revenue column ties out in total against the retiring mart's sums,
  re-sliced by daypart instead of by date.

## Out of scope
- Day-of-week as an additional grain dimension (`agg_trip_zone_daypart_dow`
  already carries that, unfiltered by billable, for a different purpose).
- Any change to `mart_revenue_component_bridge` (stays as-is, already
  monthly x service_type x borough).
- A trend/period-over-period view — `agg_trip_zone_daily`'s job, at the date
  grain being retired here; it is not itself being retired by this request.

## Open questions
- Confirm with Finance Reporting that collapsing the date dimension entirely
  (not just widening it to daypart-per-day) matches what "nobody looks at the
  daily number on its own" was actually asking for, before the retiring mart
  is dropped — this is the one part of this intent that isn't fully
  derivable from the request text alone.

## Approvals

Append-only. `capturing-intent` — not a coordinator — appends `- [x] User approved intent — YYYY-MM-DD HH:MM (UTC)` only after a structured `AskUserQuestion` response whose first-option value was `approved`. Do not append from inference.
