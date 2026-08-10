# Intent Data Slice: Airport-pickup trip fact (R6)

Companion to `intent.md`, per the
[Contextual Sampling proposal](https://github.com/accelerate-data/studio/blob/main/docs/proposals/contextual-sampling/README.md).
Cache mechanics and materialization are out of scope here — this records only
what the slice for `fct_airport_trip` should contain and why.

## 1. Model inventory

| Model | Grain | Purpose |
| --- | --- | --- |
| `fct_airport_trip` | one row per `trip_key`, pickup zone is an airport | Self-serve trip-grain fact for Commercial |

## 2. Candidate input

`core.fct_trip`, joined to `core.dim_zone` on `pickup_zone_key = zone_key` for
`is_airport_zone`. One join — the same role-playing-dimension join `fct_trip`
already resolves for every other zone attribute.

## 3. Profiling evidence

Run against `domain.duckdb`:

| Probe | Result |
| --- | --- |
| `fct_trip` total rows | 20,671,899 |
| Airport-pickup rows (`is_airport_zone`) | 1,558,413 |
| By zone | JFK 885,824 · LaGuardia 631,031 · Newark 2,481 |
| By service type | yellow 1,558,080 · green 333 |
| `airport_fee_status` | present 1,552,113 · missing 5,970 · not_applicable 333 |
| `is_billable` | true 1,519,339 · false 39,077 (~2.5%) |
| `is_fleet_attributed` | true 75,032 (~4.8%) · false 1,483,384 |

**Adequacy verdict: Ready.** Both source tables are already gold-managed and
tested; the join is the one every other airport-aware model in this warehouse
(`agg_od_flow_matrix`, `agg_trip_zone_daypart_dow`) already runs in
production.

## 4. Representative coverage requirement

~1.56M candidate rows is far more than a build/iterate loop needs — sample,
don't bring it whole. Stratify rather than take a flat random sample, so every
minority case the fact needs to prove out survives:

- **Newark (2,481 rows) — take in full.** Too small a class to risk losing
  by sub-sampling, and it's the one zone whose correct inclusion validates
  the `is_airport_zone` decision above.
- **Green-fleet rows (333) — take in full.** The only rows where
  `airport_fee_status = 'not_applicable'`; a minority class in its own right.
- **`airport_fee_status = 'missing'` rows (5,970) — take in full.** The
  boundary case distinguishing "fleet never carries this fee" from "yellow
  trip, fee value absent" — exactly what the column exists to preserve.
- **JFK and LaGuardia (the remaining bulk)** — stratified sample across
  month (6), `is_billable` (both values), and `is_fleet_attributed` (both
  values), sized in the low thousands total — enough to exercise every fee
  column and quality flag without approaching the full 1.5M.

Target slice size: on the order of a few thousand rows.

## 5. Join validation

One join, `fct_trip` → `dim_zone` on `pickup_zone_key = zone_key` — mandatory
many-to-one, already validated in production by every other model that resolves
a trip's zone. Expect zero unmatched rows and no multiplication; row count in
equals row count out.

## 6. Bounded export definition

```sql
select f.*
from core.fct_trip f
join core.dim_zone z on f.pickup_zone_key = z.zone_key
where z.is_airport_zone
  and (
    z.zone_natural_key = 1                    -- Newark, in full
    or (z.zone_natural_key in (132, 138)
        and f.service_type_key = 'green')     -- every green row, in full
    or f.airport_fee_status = 'missing'       -- every missing-fee row, in full
    -- plus a stratified sample of the remaining JFK/LaGuardia rows by
    -- month, is_billable, and is_fleet_attributed
  )
```

The exact per-stratum row cap is a model-round detail; the requirement is the
strata above, not a fixed `LIMIT`.

## 7. Business ambiguity resolved with the user

None required — profiling confirmed `is_airport_zone` already resolves the
identification question the macro's stale comment raised.
