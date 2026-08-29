# `int_status_intervals`

## Purpose and interface

One row per status event, interpreted as the interval from that event until the
next event on the same shift. It is the durable time basis for occupancy,
vehicle utilisation, and locatable idle time.

## Decisions

- Order within each shift by `event_ts`, with `event_id` as the deterministic
  tie-breaker. `received_ts` is arrival metadata and can invert the business
  event order.
- Close a terminal event at the shift's `effective_end_ts`. Leaving it open
  drops real time; using an arbitrary wall-clock boundary fabricates it.
- Floor a negative duration at zero but retain `is_negative_interval`.
  Rejecting the record would hide feed disorder, while retaining a negative
  measure would invalidate every rollup.

## Boundaries and rerun behavior

The model does not infer missing status events or alter the shift boundary; it
uses the authoritative effective end supplied by `stg_ops__shifts`. Rebuild it
after either the status-event or shift source changes, then rebuild dependent
occupancy models.

## Consumers and guardrails

`core.fct_status_interval` and `int_shift_occupancy` consume these intervals.
`assert_no_negative_status_intervals` limits how often the protective floor may
be used; a rising count is a source-quality investigation, not a reason to
change the ordering rule.

## References

- [Model SQL](../../../../transformation/models/intermediate/int_status_intervals.sql)
- [Negative-interval assertion](../../../../transformation/tests/assert_no_negative_status_intervals.sql)
