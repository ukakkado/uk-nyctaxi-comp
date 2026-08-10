# Intent Data Slice: Driver-week aggregate (R7)

Companion to `intent.md`, per the
[Contextual Sampling proposal](https://github.com/accelerate-data/studio/blob/main/docs/proposals/contextual-sampling/README.md).

## 1. Model inventory

| Model | Grain | Purpose |
| --- | --- | --- |
| `agg_driver_weekly` | one row per `driver_key` per `week_start_date` | Weekly rollup for the shift-bidding cycle |

## 2. Candidate input

`agg.agg_driver_daily` only, plus `core.dim_date` for `week_start_date` — the
same single-aggregate-source pattern `agg_driver_monthly` already uses one
level up.

## 3. Profiling evidence

| Probe | Result |
| --- | --- |
| `agg_driver_daily` row count | 62,154 |

Small, well under any sampling threshold, and already at the exact grain the
model reads from.

**Adequacy verdict: Ready.**

## 4. Representative coverage requirement

Bring the complete table as-is — no sampling. 62,154 rows is small enough
that a curated subset would cost representativeness for no size benefit, same
reasoning already applied to `agg_vehicle_monthly` in the vehicle-scorecard
slice.

## 5. Join validation

One join: `agg_driver_daily.shift_date = dim_date.calendar_date` — mandatory
many-to-one (`dim_date` is a complete date spine, every calendar day exists).
Expect zero unmatched rows, no multiplication.

## 6. Bounded export definition

```sql
select * from agg.agg_driver_daily;
select * from core.dim_date;  -- small spine, brought whole
```

## 7. Business ambiguity resolved with the user

None surfaced. Two decisions were made directly in `intent.md` rather than
raised as open questions: reusing `dim_date.week_start_date` as the week
boundary, and not flagging partial weeks at the edges of the reporting window.
