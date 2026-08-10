[title](https://github.com/accelerate-data/studio/pull/2625)# Intent Data Slice: Zone-by-daypart revenue mart (R12)

Companion to `intent.md`, per the
[Contextual Sampling proposal](https://github.com/accelerate-data/studio/blob/main/docs/proposals/contextual-sampling/README.md).

## 1. Model inventory

| Model | Grain | Purpose |
| --- | --- | --- |
| `mart_zone_daypart_revenue` | one row per (zone, daypart) | Finance's replacement for `mart_daily_zone_revenue` |
| `mart_daily_zone_revenue` (retired) | — | No data-slice needed for a retirement, only a dependency check on `monday_revenue_pack` |

## 2. Candidate input

`core.fct_trip` + `core.dim_zone` + `core.dim_daypart` — the exact join set
`mart_daily_zone_revenue` and `agg_trip_zone_daypart_dow` both already use in
production.

## 3. Profiling evidence

| Probe | Result |
| --- | --- |
| `fct_trip`, billable, in-window | 20,410,650 rows |
| Distinct zones (current version) | up to 265 (`zone_natural_key`, matching `mart_daily_zone_revenue`'s existing choice) |
| Daypart cardinality | small, fixed set from the `daypart_bands` seed via `dim_daypart` |

Combination space: ≤265 zones x a handful of dayparts — a fully enumerable,
small target grain despite the 20.4M-row source.

**Adequacy verdict: Ready.**

## 4. Representative coverage requirement

Because the output grain is small and fully enumerable, coverage means every
(zone, daypart) combination with real traffic, not a proportional random
sample of the 20.4M source rows:

- for each of the 265 zones, enough rows in each daypart it actually operates
  in to exercise every revenue-component sum (fare/tip/toll/surcharge) — a
  capped number of rows per (zone, daypart) cell is enough; the model only
  needs to prove the aggregation logic, not reproduce the true dollar totals
  locally;
- explicit, uncapped inclusion of the lowest-volume zones and the
  `'Unknown'`/`'N/A'` unresolved-zone rows CONTEXT.md flags, so an
  aggregation bug affecting sparse cells isn't hidden by the dominant zones;
- at least one non-billable and one billable trip per zone where both exist,
  to prove the ADR 0002 filter is actually gating rows, not just present in
  the `WHERE` clause unexercised.

## 5. Join validation

Two joins:

- `fct_trip` → `dim_zone`, mandatory many-to-one, same as the retiring mart
  — expect zero unmatched rows, no multiplication.
- `fct_trip` → `dim_daypart` on `pickup_hour = hour_of_day`, mandatory
  many-to-one — 24 hours each mapping to exactly one daypart; validate no
  hour maps to two dayparts and no hour is unmapped.

## 6. Bounded export definition

```sql
select f.*, z.zone_natural_key, dp.daypart_code
from core.fct_trip f
join core.dim_zone z on f.pickup_zone_key = z.zone_key
join core.dim_daypart dp on f.pickup_hour = dp.hour_of_day
where {{ in_report_window('f.pickup_datetime') }}
-- capped per (zone_natural_key, daypart_code), uncapped for the lowest-volume
-- zones and the Unknown/N/A rows
```

## 7. Business ambiguity resolved with the user

None for the model logic itself. The date-collapse grain confirmation is
recorded as an open question in `intent.md`, not guessed past.
