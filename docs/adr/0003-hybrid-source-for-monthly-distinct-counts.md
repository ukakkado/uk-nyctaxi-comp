# ADR 0003 — Hybrid source for monthly aggregates with distinct counts

**Status:** Accepted (2026-08-31)

## Context

The aggregate layer follows a pyramid pattern: each monthly model builds from the daily or hourly level directly below it (`agg_driver_monthly` from `agg_driver_daily`, `agg_vehicle_monthly` from `agg_vehicle_daily`, `agg_garage_monthly` from `agg_vehicle_monthly`). This ensures reconciliation — the monthly numbers are a rollup of the lower-grain numbers, and they cannot diverge.

When a monthly model needs **distinct counts** (e.g., distinct drivers or vehicles per zone per month), the pyramid pattern breaks. The lower-grain aggregate carries pre-aggregated distinct counts (e.g., `distinct_drivers` per hour), but these cannot be safely re-aggregated:

- **Summing** hourly distinct counts overcounts — the same driver appears in multiple hours.
- **Averaging** undercounts — a driver active for 3 hours counts as 0.25 of a driver.
- **Taking the max** is wrong — a driver active in hour 1 and hour 3 but not hour 2 counts as 1, but max(hour1=1, hour2=0, hour3=1) = 1, which happens to be correct only by accident.

The only correct approach is to compute `count(distinct)` from the fact table directly.

## Decision

When a monthly aggregate needs both **additive measures** (hours, revenue, counts that sum cleanly) and **distinct counts**, use a **hybrid source**:

- **Additive measures** roll up from the lower-grain aggregate, preserving the pyramid pattern and ensuring reconciliation.
- **Distinct counts** compute from the fact table directly, with the same grain and filters as the monthly model.

The two branches join on the monthly grain key. The distinct-count branch must apply the same dimension joins and filters as the additive branch so the zone set matches.

## Consequences

- The monthly model has **two source queries** joined on the grain key, rather than one source rolled up. This is a deviation from the pyramid pattern, but a necessary one — distinct counts cannot be re-aggregated.
- The additive measures still reconcile with the lower-grain aggregate, so the pyramid's reconciliation guarantee is preserved for the measures that support it.
- Future monthly models that need distinct counts (e.g., `agg_driver_zone_monthly`) should follow this pattern. The rationale is recorded here so the deviation is not re-litigated.
- The distinct-count branch must mirror the dimension joins and filters of the additive branch. If the additive branch uses an INNER JOIN to `dim_zone` (excluding non-current zones), the distinct-count branch must apply the same filter, or the zone sets will diverge.
