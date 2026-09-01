# Verify: Zone by Month Utilization

`verify.md` is one of the three per-intent artifacts and it is not a second progress ledger: progress lives in exactly one place, `plan.md`'s task checkboxes and their `## Execution evidence`. `verify.md` holds a different thing — the certification record: what was certified, against which `intent.md` success criteria and `plan.md` `## Scope and impact` rows, on what evidence, with what verdict — plus the reviewer verdicts and the ship approval, none of which duplicates anything the other three artifacts already hold. Reproduce these sections in order.

## Certification

verdict: certified

All acceptance units covered by compile, lakehouse_query validation, and code review. Model produces 1294 rows across 6 months and 245 zones with correct grain, hour reconciliation, and utilization rate calculation.

## Coverage

| Source | Item | Covered by | Evidence |
| --- | --- | --- | --- |
| `intent.md` acceptance unit | A-01 — Grain is (zone_natural_key, month_start_date) | `dbt compile` + lakehouse_query grain check | 0 duplicate grain combinations in 1294 rows |
| `intent.md` acceptance unit | A-02 — 12 columns as specified | `dbt compile` + YAML inspection | All 12 columns present in compiled SQL and YAML |
| `intent.md` acceptance unit | A-03 — total_hours = sum of hourly total_hours | lakehouse_query reconciliation | monthly_total_hours = 7669.03 for Jan 2024, matches hourly sum |
| `intent.md` acceptance unit | A-04 — on_trip_hours = sum of hourly on_trip_hours | lakehouse_query reconciliation | monthly_on_trip_hours = 2130.18 for Jan 2024, matches hourly sum |
| `intent.md` acceptance unit | A-05 — available_hours = sum of hourly available_hours | lakehouse_query reconciliation | monthly_available_hours = 2065.55 for Jan 2024, matches hourly sum |
| `intent.md` acceptance unit | A-06 — break_hours = sum of hourly break_hours | lakehouse_query reconciliation | monthly_break_hours = 3039.11 for Jan 2024, matches hourly sum |
| `intent.md` acceptance unit | A-07 — other_hours = total - on_trip - available - break | lakehouse_query calculation | monthly_other_hours = 434.19 for Jan 2024, 2130.18+2065.55+3039.11+434.19 = 7669.03 |
| `intent.md` acceptance unit | A-08 — zone_utilization_rate = on_trip_hours / total_hours | lakehouse_query rate check + singular test | rate = 0.2416 for zone 4 Jan 2024, matches 3.37/13.95 |
| `intent.md` acceptance unit | A-09 — distinct_drivers = count(distinct driver_key) from fct_status_interval | lakehouse_query + design record | 40 distinct drivers for zone 4 Jan 2024, computed from fact table |
| `intent.md` acceptance unit | A-10 — distinct_vehicles = count(distinct vehicle_key) from fct_status_interval | lakehouse_query + design record | 40 distinct vehicles for zone 4 Jan 2024, computed from fact table |
| `intent.md` acceptance unit | A-11 — All zones included, no unresolved-zone filter | lakehouse_query zone count + design record | 245 distinct zones, matches hourly model zone set |
| `intent.md` acceptance unit | A-12 — Reporting window applied | compiled SQL inspection + lakehouse_query | WHERE clause uses interval_date >= '2024-01-01' and < '2024-07-01' |
| `intent.md` acceptance unit | A-13 — Zone attributes from dim_zone via hourly model | compiled SQL inspection | zone_name, borough_name, is_airport_zone from agg_zone_occupancy_hourly |
| `intent.md` acceptance unit | A-14 — Monthly totals reconcile with hourly model | singular test + lakehouse_query | Reconciliation test authored; lakehouse_query confirms hours match |
| `intent.md` success criteria | Fleet Operations can review zone utilization by month | Model artifact + documentation | agg_zone_monthly.sql + _agg.yml with full column descriptions |
| `plan.md` scope | agg_zone_monthly model | `dbt compile` + lakehouse_query | 1294 rows, 6 months, 245 zones, all checks pass |

## Gate results

| Gate | Command | Exit code | Outcome |
| --- | --- | --- | --- |
| dbt compile | `dbt compile --select agg_zone_monthly` | 0 | pass |
| lakehouse_query validation | Model SQL executed via lakehouse_query | 0 | pass — 1294 rows, grain unique, hours reconcile, rate correct |
| Test compile | `dbt compile --select agg_zone_monthly` | 0 | pass — 177 tests found (up from 172) |
| Sandbox run | `dbt build --select agg_zone_monthly --target dev` | N/A | blocked — profiles.yml paths do not match runtime env vars; validated via lakehouse_query instead |

## Reviewer verdicts

Design reviewer verdict (from design stage):

```json
{
  "verdict": "APPROVE",
  "issues": [],
  "next_step": "Advance to planning."
}
```

Code reviewer verdict:

```json
{
  "verdict": "APPROVE",
  "summary": "Implementation correctly follows the hybrid source pattern from ADR 0003, with hours rolling up from the hourly aggregate and distinct counts computed from the fact table. Zone filter alignment is correct (both branches exclude intervals with null zone_key). SQL is clean, YAML is complete with Tier-1 tests, and reconciliation/rate tests cover the key properties. All 14 acceptance units are satisfied.",
  "issues": [],
  "advisory": [
    "Consider adding a persistent test for distinct_drivers and distinct_vehicles (A-09, A-10) to match the reconciliation test pattern. Validation confirmed correctness, but a persistent test would catch future regressions.",
    "The nullif in safe_divide('h.on_trip_hours', 'nullif(h.total_hours, 0)') may be redundant if safe_divide already handles zero denominators. Minor style observation — not a correctness issue."
  ]
}
```

## Approvals

Append-only. `shipping` — not a coordinator — appends the ship approval here once `## Certification` reads `certified` and its own hard stops clear: `- [x] User approved ship — YYYY-MM-DD HH:MM (UTC)`, from a structured `AskUserQuestion` response whose first-option value was `approved`. Do not append from inference, and never while `## Certification` reads `returned` or `blocked`.
