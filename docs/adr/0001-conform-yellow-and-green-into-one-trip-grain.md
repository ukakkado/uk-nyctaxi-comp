# ADR 0001 — Conform yellow and green into one trip grain

**Status:** Accepted (2023-11)

## Context

Yellow and green trip records describe the same business event but do not share a
schema. Column names differ by prefix (`tpep_` vs `lpep_`), and each fleet
carries columns the other does not:

- yellow only: `Airport_fee`
- green only: `ehail_fee`, `trip_type`

Marts were being written twice, once per fleet, and diverging.

## Decision

`silver.trips` unions both fleets onto one grain with conformed column names
and a `service_type` discriminator.

**Fleet-specific columns are dropped rather than carried as a column that is
null for one whole fleet.** A column that is structurally null for 98% of rows
invites averages that are silently wrong, and we would rather a consumer be
forced to reach for bronze deliberately than compute a wrong number by accident.

## Consequences

- Any requirement needing `Airport_fee`, `ehail_fee` or `trip_type` must read
  `bronze.yellow_tripdata` / `bronze.green_tripdata` directly and take on the
  fleet asymmetry explicitly.
- `silver.trips` is not a complete representation of a trip record. It is the
  conformed intersection, and that is deliberate.
