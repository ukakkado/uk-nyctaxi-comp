# Intent Data Slice: Vehicle scorecard

Companion to `intent.md`, produced during Requirements per the
[Contextual Sampling proposal](https://github.com/accelerate-data/studio/blob/main/docs/proposals/contextual-sampling/README.md):
the model inventory, candidate inputs, and representative-coverage evidence
that let the (single) model round build and test against a stable, source-shaped
dataset instead of the full Domain each time. Cache mechanics, materialization,
and `cache_ref` bookkeeping belong to the related Agent Cache proposal and are
out of scope here — this records only *what* data the slice for
`mart_vehicle_scorecard` should contain and *why*.

## 1. Model inventory

One model, per `intent.md`'s Deliverables inventory:

| Model | Grain | Purpose |
| --- | --- | --- |
| `mart_vehicle_scorecard` | one row per `vehicle_key` per `month_start_date` | Fleet-wide ranked vehicle performance, month by month, on the model of `mart_driver_scorecard` |

## 2. Metadata search → candidate input

`information_schema` / the dbt manifest turned up an existing model already at
the target grain: `agg.agg_vehicle_monthly` (vehicle x month, built from
`agg_vehicle_daily` with `fct_maintenance` downtime already netted in — see
`transformation/models/marts/agg/agg_vehicle_monthly.sql`).

`mart_driver_scorecard` — the model this scorecard is patterned on — reads a
single source (`agg_driver_monthly`) with no joins; it derives its ranks and
ratios entirely from window functions over that one table. The same shape
applies here: **`agg_vehicle_monthly` is the only candidate input.** No join
discovery is needed because there is no second table to join — `dim_vehicle`
and `dim_garage` are deliberately not pulled in, per `intent.md`'s Out of
scope (no vehicle-attribute segmentation, no garage-scoped rank).

## 3. Profiling evidence

Run against `domain.duckdb`, `agg.agg_vehicle_monthly` (`gold.agg_vehicle_monthly`):

| Probe | Result |
| --- | --- |
| Row count, full table | 2,625 rows, 420 distinct `vehicle_key`, 7 distinct months (2023-12 through 2024-06) |
| Row count, reporting window only (`2024-01-01` ≤ `month_start_date` < `2024-07-01`) | 2,520 rows — every one of the 420 vehicles has exactly 6 rows, one per month |
| Rows outside the reporting window | 105 rows, all `2023-12-01`, covering only 105 of the 420 vehicles |
| `online_hours`, outside-window rows | min 0.84, i.e. under an hour of activity for the whole month |
| `online_hours`, in-window rows | min 423.03, max 649.45 — no partial or near-zero months once restricted to the window |
| `revenue_per_online_hour`, in-window rows | min 15.98, max 634.93 — wide, no degenerate clustering |
| Null / zero `online_hours` | none, in or out of window (`safe_divide`'s `nullif` guard is never exercised in this data) |
| Vehicles retired before 2024-07-01 (`ops_raw.vehicle.retired_date`) | 8 of 420 — but their in-window monthly rows show no drop-off in `active_days` or `online_hours` after the retirement date (e.g. vehicle 47, retired 2024-02-17, still shows 25-28 active days and 484-530 online hours every month through June). `agg_vehicle_monthly` does not currently reflect retirement as reduced activity — a fact about the upstream aggregate, not something this model needs to compensate for |
| Vehicles per garage | even, 70 per garage across all 6 garages |

**Bronze/aggregate adequacy verdict: Ready.** No nulls on the columns this
model reads, no non-unique keys, no dtype surprises, and — once scoped to the
reporting window — no partial-month rows to reason about.

## 4. Representative coverage requirement

Because the source is small (2,520 rows once scoped to the reporting window,
well under any sampling threshold) and already uniform in every dimension the
model touches, the slice is **the complete `agg_vehicle_monthly` table
filtered to the reporting window — brought in as-is, not sub-sampled.** A
curated subset would need to reconstruct exactly the categories, months, and
garages already present in a table this size; sampling would cost
representativeness for no size benefit.

This still satisfies the coverage the model needs to build and test against:

- all 6 months of the reporting window, for every vehicle — required to prove
  month-by-month behavior (a vehicle's rank moving month to month, not just a
  single-period summary);
- the full fleet-wide spread of `revenue_per_online_hour` (15.98-634.93) —
  required to prove `rank()` behaves correctly at both ends of the table;
- all 6 garages represented, even though ranking is fleet-wide only, since
  `garage_key` is still carried through from `agg_vehicle_monthly` as a
  reference column;
- ties and near-ties in `revenue_per_online_hour` across vehicle-months, which
  the full table already contains incidentally at this volume.

Out-of-window Dec 2023 rows (105 rows, near-zero `online_hours`) are
excluded by the date-scope decision recorded in `intent.md`, not included as
a boundary case to test — the decision was to keep them out of the model
entirely, so they have no place in the slice either.

## 5. Join validation

None. `mart_vehicle_scorecard` reads a single source with no joins, mirroring
`mart_driver_scorecard`. No join-scoped selection, key propagation, or
cardinality check applies.

## 6. Bounded export definition

Source-shaped, single table, no projection changes beyond the date filter:

```sql
select *
from agg.agg_vehicle_monthly
where month_start_date >= date '2024-01-01'
  and month_start_date <  date '2024-07-01'
```

420 vehicles x 6 months = 2,520 rows. No deferred inputs — there is nothing
else this one-model intent needs later.

## 7. Business ambiguity resolved with the user

- **Date scope.** Profiling surfaced the out-of-window Dec 2023 ramp-up rows
  and their risk to an unfloored fleet-wide rank. Asked the user; resolved to
  restrict the model to the reporting window (recorded in `intent.md`'s
  Grain section).

No other ambiguity surfaced during data-slice construction — the single
source, no-join shape and the uniform in-window data left nothing else
requiring a business call.
