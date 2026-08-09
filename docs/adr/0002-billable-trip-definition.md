# ADR 0002 — The billable trip definition

**Status:** Accepted (2024-01)

## Context

Finance and Operations were reporting different trip counts for the same month.
The gap was refunds and voided trips, which Operations counted and Finance did
not.

## Decision

A **billable trip** is `total_amount > 0` with `pickup_datetime` inside the
reporting window. Every `gold` mart applies it. It is applied in gold, not in
silver, so that data-quality work can still see the excluded rows.

## Consequences

- `gold` row counts are lower than `silver.trips` and always will be.
- The filter does not exclude `payment_type` 3 (No charge) or 4 (Dispute) —
  those trips can still carry a positive `total_amount`. Whether a given metric
  should exclude them is a per-metric decision, not covered by this ADR.
