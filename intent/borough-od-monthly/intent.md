---
kind: transformation
---

# Intent: Borough-level origin-destination matrix, monthly (R8)

This file is the intent artifact: it fixes `kind:` above and records the intent approval that lets the loop advance into `design`.

## Goal
`agg_od_flow_matrix`'s zone x zone grain (up to 265 x 265 pairs) is too
granular for the board pack. Build a borough x borough view, monthly.

## Source system
`core.fct_trip`, joined twice to `core.dim_zone` (role-playing, origin and
destination) — **not** `agg_od_flow_matrix`.

**Decision.** Built fresh from `fct_trip` rather than rolling up
`agg_od_flow_matrix`, for two reasons found while inspecting it: (1) it has no
month column — it collapses the whole reporting window into one row per zone
pair, so there is no month to roll up; and (2) several of its columns
(`avg_fare`, `avg_distance`, `avg_minutes`, `avg_corridor_mph`) are
pre-averaged — re-averaging averages computed over different group sizes would
be arithmetically wrong. A fresh build from `fct_trip` is necessary, not just
cleaner.

## Target
`gold.agg` — `agg_borough_od_monthly`, next to `agg_od_flow_matrix`.

## Objects in scope
- New mart, borough x borough x month grain

## Deliverables inventory

| # | Deliverable | Kind | Notes |
| --- | --- | --- | --- |
| 1 | `agg_borough_od_monthly` | mart/model | Same measures as `agg_od_flow_matrix`, recomputed at borough x month grain directly from `fct_trip` |

## Grain
**Decision.** One row per (`origin_borough`, `destination_borough`,
`trip_month`). Role-playing `dim_zone`, joined twice, exactly as
`agg_od_flow_matrix` already does at zone grain.

## Consumers
**Decision (assumed).** No exposure in `_finance.yml` / `_ops.yml` names a
board-pack consumer today. Likely Finance or Commercial reporting; flagged as
an assumption to confirm and wire into an exposure at design time.

## Metric definitions
**Fact**, mirrors `agg_od_flow_matrix`'s measures (`trip_count`,
`total_revenue`, `avg_fare`, `avg_distance`, `avg_minutes`,
`avg_corridor_mph`), recomputed directly from `fct_trip` at the coarser grain.

**Minimum-count threshold — decision: none.** `agg_od_flow_matrix`'s `having
count(*) >= 25` exists to suppress single-digit zone-pair noise. At borough
grain there are at most 8x8 = 64 combinations per month, and even the rarest
realistic pair (e.g., Staten Island ↔ Bronx) is a real cross-borough movement
the board should see, not noise. The same threshold here would mostly be a
no-op with occasional silent suppression of a genuinely rare but real route.

Billable filter — **fact**, inherited: `is_billable` + `in_report_window`,
same as `agg_od_flow_matrix`.

## SLAs / freshness
**Fact**: nightly external build; monthly board-pack cadence (stated in the
request).

## Success criteria
- One row per origin borough x destination borough x month within the
  reporting window.
- Every measure ties out against `fct_trip` for a spot-checked borough pair
  and month.
- The board pack reads a table coarse enough that a 265x265 matrix is no
  longer the delivery vehicle.

## Out of scope
- Zone-level detail (`agg_od_flow_matrix` continues to serve that).
- A minimum-count / noise-suppression filter (decided against above).
- Wiring a specific board-pack exposure — the consumer is an assumption here,
  not confirmed.

## Open questions
- Which team formally owns the board pack and should be named as the
  exposure owner — no existing exposure names it.

## Approvals

Append-only. `capturing-intent` — not a coordinator — appends `- [x] User approved intent — YYYY-MM-DD HH:MM (UTC)` only after a structured `AskUserQuestion` response whose first-option value was `approved`. Do not append from inference.
