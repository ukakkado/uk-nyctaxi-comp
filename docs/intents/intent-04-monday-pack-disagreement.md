# Intent 04

**From:** Marta Lindqvist, Finance Reporting Lead
**To:** Data Platform
**Date:** 2024-07-16
**Needed by:** Monday. It's gone out caveated three weeks running.

---

Two tables in the Monday revenue pack disagree and I've had to footnote it three
weeks in a row.

finance.mart_daily_zone_revenue and finance.mart_monthly_service_summary should
be showing the same money over the same period. They aren't. Summed across
January to June the two totals differ, and the difference is stable week to week
— which is worse than if it moved about, because stable means it's structural
and not a timing artefact.

What I've already checked:

- Same reporting window on both.
- Both apply the billable rule from ADR 0002, as far as I can see in the SQL.
- The gap is small against the total, but it is not rounding.

I can't see what else differs between them.

What I need: which of the two I can trust, why the other one is wrong, and what
it takes to fix. The zone report is the one that goes to the CFO, so if that's
the broken one I need to know before Monday rather than after.
