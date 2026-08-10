# Intent Data Slice: Extend reporting window through 2023 (R11)

Companion to `intent.md`, per the
[Contextual Sampling proposal](https://github.com/accelerate-data/studio/blob/main/docs/proposals/contextual-sampling/README.md).

## No slice — deferred

There is no 2023 source data in this domain to profile, sample, or export.
Profiling found only 40 stray pre-2024 rows in `silver.trips` against
20,671,899 in the real Jan–Jun 2024 window — not a sample-worthy population,
an absence.

The proposal's own vocabulary for this case is a **deferred catalogue entry**
(Section 13): an approved dependency with no physical data yet, registered
only once deliverable 1 (2023 ingestion, owned outside this repo) lands and an
exact bounded refresh recipe can be validated against real rows. Recording it
as deferred here rather than guessing at a slice keeps the gap visible instead
of silently treating "no data" as "small data, bring as-is."

Once `bronze`/`silver` carry 2023 data, this intent's data-slice work is
deliverable 2's: extend the same `in_report_window` bounded query every
finance mart already uses —

```sql
{{ in_report_window('f.pickup_datetime') }}
-- report_start moved to 2023-01-01 (or 2023-01-01–2023-07-01, per the open
-- question in intent.md), report_end unchanged
```

— no new sampling logic required, since the macro and the marts that use it
are already parameterized on the vars, not hardcoded to 2024.
