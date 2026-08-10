---
kind: ingestion
---

# Intent: Extend the reporting window back through 2023 (R11)

This file is the intent artifact: it fixes `kind:` above and records the intent approval that lets the loop advance into `design`. `kind: ingestion` reflects the blocking deliverable below — the second deliverable is trivial transformation once the first lands.

## Goal
Extend the reporting window on the finance marts back through 2023, so the
board's year-on-year question can be answered.

## Blocking fact, discovered during intake
This repo's dbt project only **consumes** `bronze`/`silver` as dbt sources —
it does not ingest data (`CONTEXT.md`: "bronze and silver are ... produced by
the loader outside this repo"). Profiling `silver.trips` shows only **40
rows** with `pickup_datetime` before 2024-01-01, against 20,671,899 rows in
the Jan–Jun 2024 window, and this project's own data-provenance notes confirm
the real TLC extract only covers Jan–Jun 2024. **There is no 2023 trip volume
in this domain to extend the window into.** `report_start` is a dbt var, but
changing it without new data landing upstream would just widen a filter over
rows that mostly don't exist.

## Source system
None available in-repo for 2023 trip data. Requires the external loader team
to land 2023 TLC bronze/silver extracts first — outside this repo's dbt
project boundary.

## Target
`gold.finance` marts (`mart_daily_zone_revenue`, `mart_monthly_service_summary`,
`mart_revenue_component_bridge`) — once 2023 source data exists, the change
itself is a one-line `report_start` var edit plus a rebuild; no model logic
changes.

## Objects in scope
- 2023 TLC trip data landed into `bronze`/`silver` (owned outside this repo)
- `report_start` var change + finance-mart rebuild, once the above exists

## Deliverables inventory

| # | Deliverable | Kind | Notes |
| --- | --- | --- | --- |
| 1 | 2023 TLC trip data landed in `bronze`/`silver` | source connection | **Blocking.** Owned by the external loader/platform team — this repo only declares `bronze`/`silver` as sources, it cannot ingest into them |
| 2 | Extend `report_start` to 2023 and rebuild finance marts | mart/model | Trivial once (1) exists; only the var and a full historical rebuild, no model logic changes |

## Success criteria
- Deliverable 1: 2023 TLC yellow/green trip data is queryable in
  `bronze`/`silver` at the same schema and grain as the existing Jan–Jun 2024
  data.
- Deliverable 2: finance marts report year-on-year 2023 vs. 2024 figures once
  rebuilt.

## Out of scope
- Any change to the reporting-window mechanism itself (`in_report_window`
  macro, `report_start`/`report_end` vars) — the mechanism already supports
  any date range; only the value and the underlying data are missing.
- Building deliverable 2 before deliverable 1 lands — sequencing is fixed,
  not a parallelizable pair.

## Open questions
- Does "through 2023" mean all of calendar 2023 (`2023-01-01` onward), or
  only enough of 2023 for a same-period year-on-year comparison against the
  existing Jan–Jun 2024 window (`2023-01-01` to `2023-07-01`)? This changes
  how much 2023 data needs to land, not just the var value.
  **Recommendation if forced to pick:** the same-period comparison
  (`2023-01-01` to `2023-07-01`) — that's what "year-on-year" against an
  existing Jan–Jun window actually compares; asking the loader team for a
  full extra half-year the board question doesn't need yet would be
  over-scoping the ingestion ask.

## Approvals

Append-only. `capturing-intent` — not a coordinator — appends `- [x] User approved intent — YYYY-MM-DD HH:MM (UTC)` only after a structured `AskUserQuestion` response whose first-option value was `approved`. Do not append from inference.
