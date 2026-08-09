---
kind: transformation
---

# Intent: Airport trip economics

## Originating request

> Finance is supporting the Port Authority concession renegotiation at LaGuardia
> and JFK. They want a view of what airport pickups actually earn us — revenue,
> tips, and how that varies across the day and by where the trip goes. Can we
> get them a mart for this before end of quarter?

## Classification

| Axis | Verdict | Rationale |
| --- | --- | --- |
| `action` | `work` | The request produces a new data product, not a review or an opinion. |
| `kind` | `transformation` | A new dbt mart over existing conformed sources. No new source connection, no schedule, no semantic model. |
| `scale` | `product` | New mart plus supporting model(s); beyond a bounded operation. |

## Goal

Give Finance a defensible per-period view of the economics of airport pickups so
that concession terms can be negotiated against measured revenue rather than
against anecdote.

## Source system

Existing warehouse only. `silver.trips`, `silver.zones`, `silver.payment_types`,
`bronze.yellow_tripdata`. No new source connection.

## Target

`gold` schema in the analytics warehouse, dbt-managed, this repo.

## Objects in scope

- New mart(s) under `dbt/models/marts/`
- Existing `dim_zone` (read; possibly extended with an airport flag)

## Deliverables inventory

| # | Deliverable | Kind | Notes |
| --- | --- | --- | --- |
| 1 | Airport trip economics mart | mart/model | Grain, metric set and cohort under interview |

## Success criteria

- TBD from interview

## Out of scope

- New source connections — the request needs no data the warehouse lacks
- Any change to `mart_daily_zone_revenue` or `mart_monthly_service_summary`
- Scheduling and semantic-layer changes

## Facts established before interview

Read, not asked. Sources cited.

| # | Fact | Value | Source |
| --- | --- | --- | --- |
| F1 | Airport zones are three, not two | `132` JFK, `138` LaGuardia, `1` Newark | `silver.zones` |
| F2 | `service_zone = 'Airports'` **excludes Newark** — EWR carries `service_zone = 'EWR'` | Filtering on `'Airports'` silently drops 2,551 trips | `silver.zones` |
| F3 | Airport pickups are 7.5% of all trips | 1,558,426 of 20,671,899 | `silver.trips` |
| F4 | Airport dropoffs are a different, smaller population | 528,295; only 83,147 trips have an airport at both ends | `silver.trips` |
| F5 | Green taxis are structurally absent from airports | 333 of 1,558,426 airport pickups = 0.02% | `silver.trips` |
| F6 | `Airport_fee` does not exist in silver | Only on `bronze.yellow_tripdata`; ADR 0001 dropped it when conforming | `information_schema`, ADR 0001 |
| F7 | `Airport_fee` is not clean | 1,543,243 rows at `1.75`, but also 38,695 at `-1.75`, 22 at `1.25`, and 1,975,985 NULL fleet-wide | `bronze.yellow_tripdata` |
| F8 | Newark pickups do not carry the surcharge | 2,525 of 2,539 EWR pickups have `Airport_fee = 0.00` | `bronze.yellow_tripdata` |
| F9 | JFK runs on a flat fare | `rate_code_id = 2` (JFK) on 480,597 airport pickups | `silver.trips` |
| F10 | Cash tips are unmeasured, not zero | 0.04% of 291,752 cash airport trips record a tip, vs 94.2% of card | `silver.trips`, `CONTEXT.md` |
| F11 | Disputes are mostly non-positive | 22,758 of 48,797 dispute trips have `total_amount <= 0`; mean total $3.38 | `silver.trips` |
| F12 | The trip → zone join is clean | 0 unmatched, 0 fanout, max 1 match per left key over all 20.67M rows | `join_evidence` |
| F13 | Zone ids 264/265 join cleanly but carry no borough | Matched-but-meaningless, not unmatched | `silver.zones`, `CONTEXT.md` |
| F14 | Freshness is already fixed | Loader + `dbt build` nightly 03:00 ET, externally scheduled | `CONTEXT.md` |
| F15 | Consumers named | Finance owns this request; Operations reporting is the other existing gold consumer | `CONTEXT.md` |

## Open questions

- Under interview

## Approvals

_None yet._
