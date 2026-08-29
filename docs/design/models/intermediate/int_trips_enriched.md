# `int_trips_enriched`

## Purpose and interface

One row per conformed `trip_key`. This is the only intermediate model that
rejoins the fleet-specific attributes removed from `silver.trips`:
`airport_fee` for Yellow, and `ehail_fee` / `trip_type` for Green.

## Decisions

- Rejoin through the two dedicated, deduplicated staging models on `trip_key`.
  Joining raw Bronze rows would allow duplicate source records to multiply a
  trip; carrying all fleet-specific columns in `silver.trips` would reverse
  ADR 0001's conformed-intersection contract.
- Preserve three airport-fee states: `present`, `missing`, and
  `not_applicable`. A null Green fee is not missing data; it is a field that
  does not exist for that fleet. Collapsing the states would corrupt
  fleet-blind fee metrics.
- Use left joins. Every conformed trip survives even when its optional,
  fleet-specific companion is absent; the staging models enforce the required
  at-most-one match.

## Boundaries and rerun behavior

This model restores attributes; it does not apply finance filters, quality
filters, or fleet attribution. Its upstream inputs are `stg_tlc__trips`,
`stg_tlc__yellow_trip_extras`, and `stg_tlc__green_trip_extras`; rebuild it
whenever any of those sources are rebuilt.

## Consumers and guardrails

`int_trip_fare_components`, `int_trip_quality_flags`, and ultimately
`core.fct_trip` depend on this contract. The `airport_fee_status` accepted-value
test and `assert_airport_fee_only_on_yellow` protect its fleet asymmetry.

## References

- [ADR 0001](../../../adr/0001-conform-yellow-and-green-into-one-trip-grain.md)
- [Model SQL](../../../../transformation/models/intermediate/int_trips_enriched.sql)
