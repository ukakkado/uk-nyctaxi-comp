# Intent Data Slice: Borough OD matrix, monthly (R8)

Companion to `intent.md`, per the
[Contextual Sampling proposal](https://github.com/accelerate-data/studio/blob/main/docs/proposals/contextual-sampling/README.md).

## 1. Model inventory

| Model | Grain | Purpose |
| --- | --- | --- |
| `agg_borough_od_monthly` | one row per (origin borough, dest borough, month) | Board-pack OD view, coarse enough to read directly |

## 2. Candidate input

`core.fct_trip`, joined twice to `core.dim_zone` (origin, destination) — the
exact role-playing technique `agg_od_flow_matrix` already runs in production.

## 3. Profiling evidence

| Probe | Result |
| --- | --- |
| `fct_trip`, billable, in-window | 20,410,650 rows |
| Monthly spread | 2.99M (Jan) – 3.74M (May), fairly even across 6 months |
| Distinct current-version boroughs (`dim_zone`) | 8 (Bronx, Brooklyn, EWR, Manhattan, N/A, Queens, Staten Island, Unknown) |

Up to 8x8 = 64 origin/destination combinations per month, ≤384 across the
6-month window — a small, fully enumerable target grain despite the 20.4M-row
source.

**Adequacy verdict: Ready.**

## 4. Representative coverage requirement

20.4M candidate rows is far too large to bring as-is. Because the target grain
is small and fully enumerable, the requirement is coverage of every
combination that occurs, not a random trip sample:

- for every (origin borough, dest borough, month) combination present in
  `fct_trip`, enough rows to exercise the measures faithfully — a bounded
  per-combination cap, since the model only needs to prove the aggregation
  logic against a shape it will see, not reproduce true totals locally;
- explicit, uncapped inclusion of the rare pairs — anything touching Staten
  Island, or 'Unknown'/'N/A' boroughs — the combinations most likely to be
  silently dropped or miscounted by an aggregation bug;
- both intra-borough (`is_intra_borough = true`, the dominant case, e.g.
  Manhattan → Manhattan) and inter-borough pairs.

## 5. Join validation

Two joins, `fct_trip` → `dim_zone` (pickup) and `fct_trip` → `dim_zone`
(dropoff) — both mandatory many-to-one, exactly as `agg_od_flow_matrix`
already validates in production. Expect zero unmatched rows on each side, no
multiplication.

## 6. Bounded export definition

```sql
select f.*
from core.fct_trip f
where {{ in_report_window('f.pickup_datetime') }}
  and f.is_billable
-- stratified/capped per (pickup borough, dropoff borough, month) combination,
-- uncapped for any combination touching Staten Island, Unknown, or N/A
```

## 7. Business ambiguity resolved with the user

None required for the model logic. The board-pack owner is recorded as an
open question in `intent.md` rather than guessed.
