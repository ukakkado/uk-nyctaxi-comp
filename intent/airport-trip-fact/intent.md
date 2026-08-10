---
kind: transformation
---

# Intent: Airport-pickup trip fact (R6)

This file is the intent artifact: it fixes `kind:` above and records the intent approval that lets the loop advance into `design`.

## Goal
Commercial currently has to ask Data Platform for airport-pickup trip data
with fee components every time they need it. Build a trip-grain fact
restricted to airport pickups, carrying the fee components, so Commercial can
query it directly.

## Source system
`core.fct_trip`, joined to `core.dim_zone` for airport identification.

## Target
`gold.core` — a new fact table alongside `fct_trip`, `fct_shift`,
`fct_status_interval`, `fct_maintenance`.

## Objects in scope
- New fact table `fct_airport_trip` — trip grain, airport pickups only

## Deliverables inventory

| # | Deliverable | Kind | Notes |
| --- | --- | --- | --- |
| 1 | `fct_airport_trip` | mart/model | Trip-grain fact, filtered to airport pickups, carrying every fee component `fct_trip` already carries |

## Grain
One row per `trip_key`, where the pickup zone is an airport (Newark, JFK,
LaGuardia) — same grain as `fct_trip`, just filtered, not a new business event.

**Decision.** Airport identification uses `dim_zone.is_airport_zone`, not the
unused `airport_zone_ids()` macro. The macro's own comment warns that Newark's
`tlc_service_zone` is `'EWR'`, not `'Airports'` — but profiling confirms
`is_airport_zone` already includes Newark correctly (2,481 EWR rows found via
the flag), because it comes from master data directly, not from
`tlc_service_zone`. The macro is dead code solving a problem `is_airport_zone`
doesn't have.

## Consumers
Commercial — **fact**, stated directly in the request. No existing exposure
names Commercial against a trip-grain object (`concession_negotiation_pack`
reads `mart_monthly_service_summary` only). **Decision (assumed):** treat this
as a new consumer; wiring an exposure is a design-time follow-up, not part of
this intent's deliverable.

## Metric definitions
- Fee components — **fact**, identical to `fct_trip`: `fare_amount`, `extra`,
  `mta_tax`, `improvement_surcharge`, `congestion_surcharge`, `tolls_amount`,
  `tip_amount`, `airport_fee`, `total_surcharges` (macro), `fare_residual`
  (macro), `total_amount`.
- Billable filter — **decision**, not applied. Every airport-pickup trip is
  carried, with `is_billable` as a column, mirroring `fct_trip`'s own
  philosophy of leaving the ADR 0002 filter to the marts that need it, rather
  than finance's revenue marts, which do pre-apply it. This is a fact table,
  not a revenue mart.
- Materialization — **decision**, mirror `fct_trip`'s `incremental`
  config (`unique_key: trip_key`, filtered on `pickup_datetime`), since this
  is a straight filter of an already-incremental fact.

## SLAs / freshness
**Fact**, from `CONTEXT.md`: same nightly external build as `fct_trip`.

## Success criteria
- `fct_airport_trip` has exactly one row per `trip_key` where the pickup zone
  is JFK, LaGuardia, or Newark.
- Every fee-component column on `fct_trip` is present unchanged.
- Commercial can query it directly without joining the full ~20M-row
  `fct_trip`.

## Out of scope
- Applying the billable filter (left to the consumer).
- Dropoff-airport trips (return legs) — "airport pickups" is pickup-side
  only, per the request's own wording.
- Building a dedicated Commercial exposure/dashboard — noted as a design-time
  follow-up, not delivered here.

## Open questions
- None.

## Approvals

Append-only. `capturing-intent` — not a coordinator — appends `- [x] User approved intent — YYYY-MM-DD HH:MM (UTC)` only after a structured `AskUserQuestion` response whose first-option value was `approved`. Do not append from inference.
