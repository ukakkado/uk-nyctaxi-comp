# Intent Data Slice: Garage-by-week utilisation

Companion to `intent.md`, per the
[Contextual Sampling proposal](https://github.com/accelerate-data/studio/blob/main/docs/proposals/contextual-sampling/README.md).

## 1. Model inventory

| Model | Grain | Purpose |
| --- | --- | --- |
| `mart_garage_utilisation` | one row per `garage_key` per `week_start_date` | Garage-level "sitting vs. earning" comparison, week over week |

## 2. Candidate input

`agg.agg_vehicle_daily` (the level directly below the target grain) joined to
`core.dim_garage`, plus `core.fct_maintenance` for downtime and
`core.dim_date` for `week_start_date` — no raw fact needed; every measure
this mart carries already rolls up cleanly from these three.

## 3. Profiling evidence

| Probe | Result |
| --- | --- |
| `agg_vehicle_daily` row count | 65,709 |
| `agg_vehicle_daily` date range | 2023-12-31 to 2024-06-30 |
| `agg_vehicle_daily` rows before the reporting window (`shift_date < 2024-01-01`) | 105, all distinct vehicles (one partial day each) |
| `agg_vehicle_daily` row count, restricted to the reporting window (2024-01-01 to 2024-06-30) | 65,604 |
| Distinct `vehicle_key` | 420 |
| Distinct `garage_key` | 6 |
| `agg_vehicle_daily` rows with a null `garage_key` | 0 |
| `dim_garage` row count | 6 (`bay_capacity` 30-140, one per garage) |
| Distinct weeks in-window (`date_trunc('week', shift_date)`) | 26, running 2024-01-01 to 2024-06-24 |
| `fct_maintenance` row count | 848 |
| `fct_maintenance` date range (`started_date`) | 2024-01-01 to 2024-06-28 — no Dec-2023 leak |
| `fct_maintenance` distinct `garage_key` / `vehicle_key` | 6 / 411 |
| `fct_maintenance` `sum(down_days)` / `sum(cost_usd)` | 2,063 / 1,118,696 |
| Distinct weeks in `fct_maintenance` (`date_trunc('week', started_date)`) | 26 |

`2024-01-01` is a Monday, so `date_trunc('week', ...)` lands exactly on the
reporting window's own boundaries — 26 clean weeks, no partial first or last
week to flag, unlike `agg_vehicle_daily`'s partial Dec-2023 tail (105 rows,
one day each, outside the reporting window already by `intent.md`'s decision
to source only `agg_vehicle_daily`, not raw shifts).

**Adequacy verdict: Ready.** Both inputs are small and already at or one
step below the target grain.

## 4. Representative coverage requirement

Bring both tables complete, no sampling:

- `agg_vehicle_daily`, restricted to the reporting window
  (`shift_date >= '2024-01-01' and shift_date < '2024-07-01'`) — 65,604 rows,
  covering all 420 vehicles and all 6 garages, well under any sampling
  threshold, same reasoning already applied to `agg_driver_daily` in the
  driver-weekly slice.
- `fct_maintenance` complete — 848 rows, all 6 garages already represented
  with no minority-garage risk.
- `dim_garage` and `dim_date` complete — 6 rows and a date spine,
  respectively, brought whole as dimension/spine tables always are in this
  warehouse's slices.

## 5. Join validation

| Join | Expectation |
| --- | --- |
| `agg_vehicle_daily.garage_key = dim_garage.garage_key` | Mandatory many-to-one. `agg_vehicle_daily` carries 0 null `garage_key` rows and every vehicle's garage exists in `dim_garage`'s 6 rows — no unmatched rows, no fanout. |
| `agg_vehicle_daily.shift_date = dim_date.calendar_date` | Mandatory many-to-one against a complete date spine, same expectation already validated for `agg_driver_weekly`. |
| `fct_maintenance.garage_key` rolled to week, unioned into the garage-week grain | One-to-many from `fct_maintenance` into garage-weeks (0-or-more maintenance rows per garage-week); expect some garage-weeks with no maintenance row at all (848 events over 6 garages x 26 weeks = 156 garage-weeks, so most garage-weeks carry zero events) — those weeks' `down_days` / `maintenance_cost` must default to 0, not null. |

## 6. Bounded export definition

```sql
select *
from agg.agg_vehicle_daily
where shift_date >= '2024-01-01' and shift_date < '2024-07-01';

select * from core.dim_garage;

select * from core.fct_maintenance;

select * from core.dim_date
where calendar_date >= '2024-01-01' and calendar_date < '2024-07-01';
```

## 7. Business ambiguity resolved with the user

None surfaced. Every construction decision — sourcing from `agg_vehicle_daily`
rather than a nonexistent garage-day aggregate, reading `down_days` /
`maintenance_cost` from `fct_maintenance` directly rather than expecting
`agg_vehicle_daily` to carry them, and reusing `dim_date.week_start_date` as
the week boundary — was made directly in `intent.md` rather than raised as an
open question, each with its precedent cited.
