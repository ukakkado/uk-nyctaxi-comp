---
status: decided
date: 2026-08-29
---

# Status-based aggregates source from the interval fact, not from pre-aggregated hourly models

When building a status-based aggregate at a coarser grain than `agg_zone_occupancy_hourly` (e.g. zone × month), source from `core.fct_status_interval` directly rather than rolling up the hourly model. The hourly model collapses `AVAILABLE` and `DISPATCHED` into separate columns but does not preserve the raw status_code needed for arbitrary status-group breakdowns at a new grain.

## Considered Options

- **Roll up `agg_zone_occupancy_hourly` to the target grain.** Simpler SQL, but the hourly model's columns are fixed at build time. Adding a new status grouping (e.g. `idle_hours = AVAILABLE + DISPATCHED`) requires modifying the hourly model first, which couples the new aggregate's contract to an existing model's schema.

- **Source from `fct_status_interval` directly.** More rows to aggregate, but preserves the full status_code column and allows arbitrary status-group definitions at the target grain without touching the hourly model. The 189K zone-resolved rows are small enough that the aggregation cost is negligible.

## Consequences

- New status-based aggregates at any grain coarser than hourly should source from `fct_status_interval` (or `int_status_intervals` if they need pre-zone-join rows), not from `agg_zone_occupancy_hourly`.
- The hourly model remains the canonical hourly-grain occupancy view; it is not the building block for coarser grains.
- If the hourly model's schema changes (e.g. a new status column), coarser-grain models are unaffected because they do not depend on it.
