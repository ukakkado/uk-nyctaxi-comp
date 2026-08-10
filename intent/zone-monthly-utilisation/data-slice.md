# Intent Data Slice: Zone-by-month utilisation (R10)

Companion to `intent.md`, per the
[Contextual Sampling proposal](https://github.com/accelerate-data/studio/blob/main/docs/proposals/contextual-sampling/README.md).

## 1. Model inventory

| Model | Grain | Purpose |
| --- | --- | --- |
| `mart_zone_utilisation` | one row per zone per month | Zone-level "sitting vs. earning" comparison |

## 2. Candidate input

`agg.agg_zone_occupancy_hourly` only, plus a `date_trunc('month', ...)` of
`interval_date` — no additional table needed.

## 3. Profiling evidence

| Probe | Result |
| --- | --- |
| `fct_status_interval` row count (the level below the candidate input) | 3,775,364 |
| Distinct zones | 259 |
| Date range | 2023-12-31 to 2024-07-01 |
| Status codes present | ON_TRIP, DISPATCHED, AVAILABLE, BREAK, LOGIN, LOGOUT |
| Negative intervals | 0 |
| Terminal intervals (shift-end truncation) | 73,041 |

`agg_zone_occupancy_hourly` only buckets `ON_TRIP`/`AVAILABLE`/`BREAK` hours
explicitly — `LOGIN`/`DISPATCHED`/`LOGOUT` hours don't roll into any of its
three named columns, so they won't sum to `total_hours`. That's an existing
property of the aggregate this intent builds on, not something introduced or
fixed here.

**Adequacy verdict: Ready**, with a note: `agg_zone_occupancy_hourly`'s own
row count wasn't profiled directly in this pass (it's a derived aggregate, not
a raw source) — recommend profiling it at design time before deciding
full-table-vs-sampled for this model's actual input.

## 4. Representative coverage requirement

`agg_zone_occupancy_hourly` is zone x hour x daypart — at most 259 zones x
~4,392 hours (6 months), smaller than the base fact but not yet confirmed to
be small in absolute terms. Recommendation:

- if its row count comes in near the same order as `agg_driver_daily`
  (tens of thousands), bring it as-is, no sampling;
- otherwise, stratify by zone — including a deliberate mix of the 3 airport
  zones (already flagged via `is_airport_zone`) and a spread of non-airport
  zones — and by month, sized to exercise every measure without approaching
  the full table.

## 5. Join validation

None beyond what `agg_zone_occupancy_hourly` already validates in production
(its own join from `fct_status_interval` to `dim_zone`). This model only
truncates the date and re-aggregates — no new join.

## 6. Bounded export definition

```sql
select date_trunc('month', interval_date) as month_start_date, *
from agg.agg_zone_occupancy_hourly
-- whole table if row count is small (same order as agg_driver_daily);
-- otherwise stratified by zone_natural_key (all 3 airport zones in full)
-- and month, per the coverage requirement above
```

## 7. Business ambiguity resolved with the user

None for the model logic. The `zone_key` vs. `zone_natural_key` grain choice
is left open in `intent.md`.
