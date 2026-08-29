# `fct_trip`

## Purpose and interface

The warehouse trip contract: one row per TLC `trip_key`, with conformed trip
measures, role-playing zone keys, effective-dated reference keys, quality
status, and optional Harbour Point fleet attribution.

## Decisions

- Retain every conformed trip and expose `is_billable`; revenue marts opt into
  the billable definition. Filtering the fact would prevent quality and
  operational analysis of refunds, voids, and meter errors.
- Resolve pickup and dropoff zones separately, and resolve zones and vendors
  as of the pickup date using half-open validity ranges. Current-version joins
  would rewrite history; natural-key-only joins can multiply rows.
- Preserve a null driver, vehicle, and shift for trips outside the synthetic
  Harbour Point fleet, and make the meaning explicit with
  `is_fleet_attributed`. Null is an expected coverage boundary, not a failed
  dimension lookup.
- Materialize incrementally by `trip_key`. The incremental predicate only
  processes pickups later than the maximum already loaded timestamp; a
  correction or late-arriving trip at or before that boundary requires a full
  refresh.

## Boundaries and guardrails

This fact owns conformed trip identity and dimensional resolution, not finance
aggregation, status sessionization, or lease economics. The row-count assertion
against `stg_tlc__trips` is the primary contract: no join may add or remove a
trip.

## Consumers

All trip-level finance, aggregate, and trip-quality marts use this model. Its
fee fields originate in `int_trips_enriched`; see that design record for the
fleet-specific field contract.

## References

- [ADR 0001](../../../adr/0001-conform-yellow-and-green-into-one-trip-grain.md)
- [ADR 0002](../../../adr/0002-billable-trip-definition.md)
- [Enrichment design](../intermediate/int_trips_enriched.md)
- [Model SQL](../../../../transformation/models/marts/core/fct_trip.sql)
- [Row-count assertion](../../../../transformation/tests/assert_fct_trip_matches_silver_rowcount.sql)
