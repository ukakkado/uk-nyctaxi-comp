---
kind: transformation
---

# Intent: Weather dimension on core.fct_trip (R9)

This file is the intent artifact: it fixes `kind:` above and records the intent approval that lets the loop advance into `design`.

## Goal
Add a weather dimension onto `core.fct_trip` so demand can be sliced by
conditions at the trip grain, not only through the existing borough+day
aggregate (`agg_weather_demand_daily`).

## Source system
`mdm_raw.weather_daily` (via `stg_mdm__weather`) for the new dimension;
`core.fct_trip` + `core.dim_zone` for the join key (trip's pickup date + pickup
zone's borough).

## Target
`gold.core` — new `dim_weather` model, plus a `weather_key` column added to
the existing `fct_trip` model.

## Objects in scope
- New dimension: `dim_weather`
- Extend `fct_trip` with a `weather_key` foreign key

## Deliverables inventory

| # | Deliverable | Kind | Notes |
| --- | --- | --- | --- |
| 1 | `dim_weather` | mart/model | New Type 1 dimension |
| 2 | `fct_trip.weather_key` | mart/model | Additive column on an existing incremental model |

## Grain
`dim_weather` — **decision**: Type 1, one row per (`obs_date`,
`borough_name`). **Fact** supporting the decision: `weather_daily` carries no
`valid_from`/`valid_to` columns the way `dim_zone` does — there is nothing to
version, so Type 1 is the only fit.

`fct_trip.weather_key` — resolved by joining the trip's `pickup_date` to
`obs_date` and the trip's pickup zone's `borough_name` to weather's
`borough_name` — the exact join `agg_weather_demand_daily` already performs
in production, pushed down to the trip grain instead of a pre-aggregate.

## Consumers
**Fact**: this widens `fct_trip`, so every existing consumer is a consumer by
extension (additive column, no behavior change for them). The new slicing
capability itself has no named consumer beyond "so we can slice demand by
conditions." **Decision (assumed):** Operations/Commercial demand analysis, to
confirm at design time.

## Metric definitions
**Fact**: `weather_class` / `is_wet_day` / `is_snow_day` thresholds are
already defined on `agg_weather_demand_daily` (snow > 0.5in, precip > 0.10in,
temp > 80F hot, < 32F freezing) — carried onto `dim_weather` unchanged, not
redefined.

**Null handling — fact/decision.** Trips whose pickup zone resolves to
borough `'Unknown'` or `'N/A'` (CONTEXT.md's zone-id 264/265 characteristic)
have no matching weather row; `weather_key` is null by construction. Same
"real absence, not missing data" philosophy `fct_trip` already applies to
`is_fleet_attributed`. No synthetic weather value is invented for these.

## SLAs / freshness
**Fact**: nightly external build; `weather_daily` already covers exactly the
reporting window (182 days, 2024-01-01 to 2024-06-30, all 6 non-code
boroughs).

## Success criteria
- `dim_weather` has one row per (`obs_date`, `borough_name`) present in
  `weather_daily`.
- `fct_trip.weather_key` resolves for every trip whose pickup zone has a real
  borough, and is null — not a fabricated default — for `'Unknown'`/`'N/A'`.
- A trip-grain query can slice demand by `weather_class` without a separate
  aggregate.

## Out of scope
- Changing `agg_weather_demand_daily` (stays as the existing borough+day
  aggregate; this is a separate, trip-grain capability).
- Backfilling weather history beyond what `weather_daily` already contains.
- Any change to `fct_trip`'s existing incremental `unique_key` or grain —
  purely an additive column.

## Open questions
- `fct_trip` is `materialized = 'incremental'` with `delete+insert`. Adding a
  column to an already-built incremental table needs either a full-refresh
  or an `on_schema_change` setting. Flagged for design/plan — it's an
  execution mechanic, not a business-scope question; it doesn't change what
  `dim_weather` or `weather_key` mean.

## Approvals

Append-only. `capturing-intent` — not a coordinator — appends `- [x] User approved intent — YYYY-MM-DD HH:MM (UTC)` only after a structured `AskUserQuestion` response whose first-option value was `approved`. Do not append from inference.
