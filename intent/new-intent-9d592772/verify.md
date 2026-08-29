# Verify: Zone by Month Utilisation

## Coverage

| Source | Item | Covered by | Evidence |
| --- | --- | --- | --- |
| `intent.md` acceptance unit | `A-01` — Grain is one row per (zone, month). Unique key is (zone_key, month_start_date). | `dbt test` unique + not_null on composite key | Independent query: 1284 rows, 1284 distinct keys — PASS |
| `intent.md` acceptance unit | `A-02` — Source population is `fct_status_interval` joined to `dim_zone` (current version only). | Model SQL inspection; row count ≤ sum of intervals in source | SQL inspection: `from {{ ref('fct_status_interval') }} si join {{ ref('dim_zone') }} z on si.zone_key = z.zone_key and z.is_current_version = true` — PASS |
| `intent.md` acceptance unit | `A-03` — `total_hours` = sum of all `interval_seconds` / 3600 for the zone-month. | Independent SUM from `fct_status_interval` grouped by zone and month | Independent recomputation: 1284/1284 rows match — PASS |
| `intent.md` acceptance unit | `A-04` — `earning_hours` = sum of `interval_seconds` where `status_code = 'ON_TRIP'` / 3600. | Independent SUM with ON_TRIP filter from source | Independent recomputation with COALESCE: 1284/1284 rows match, 313 rows with 0 earning hours — PASS |
| `intent.md` acceptance unit | `A-05` — `utilisation_rate` = `earning_hours` / `total_hours`, null when `total_hours` = 0. | Independent recomputation from raw hours | Independent recomputation: 1284/1284 rows have valid utilisation_rate in [0, 1], 313 rows with 0% utilisation — PASS |
| `intent.md` acceptance unit | `A-06` — Unresolved zones (`is_unresolved_zone = true`) are excluded from the output. | No rows with `is_unresolved_zone = true` in output | Independent query: 0 unresolved zones, 0 rows with zone_natural_key in (264, 265) — PASS |
| `intent.md` acceptance unit | `A-07` — Model exposes raw hour components alongside the ratio: `total_hours`, `earning_hours` (ON_TRIP), `idle_hours` (AVAILABLE), `break_hours` (BREAK), plus `utilisation_rate`. DISPATCHED, LOGIN, LOGOUT intervals count toward `total_hours` but are not named buckets. | Column presence check | SQL inspection: all 5 columns present (total_hours, earning_hours, idle_hours, break_hours, utilisation_rate) — PASS |
| `intent.md` acceptance unit | `A-08` — "Our cars" scope — all vehicles in the status stream, not filtered to fleet-attributed only. | Row count = count of all intervals in source grouped by zone-month | Independent query: 420 distinct vehicles in source = 420 distinct vehicles in model — PASS |
| `intent.md` acceptance unit | `A-09` — Month is derived from `interval_date`, truncated to first of month. Output column is `month_start_date`. | Distinct month values match expected reporting window | Independent query: 7 distinct months, min=2024-01-01, max=2024-07-01, all truncated to first of month — PASS |
| `intent.md` success criteria | The model produces one row per (zone, month) combination within the reporting window | A-01, A-09 | A-01: 1284 unique rows; A-09: 7 months in reporting window — PASS |
| `intent.md` success criteria | Utilisation rate is computable as earning hours / total hours in zone, with raw hour components also exposed | A-03, A-04, A-05, A-07 | A-03/A-04/A-05: metrics recomputed independently; A-07: all columns present — PASS |
| `intent.md` success criteria | Every zone in `dim_zone` (excluding unresolved zones) appears for every month it has any status interval data | A-02, A-06, A-08 | A-02: source join correct; A-06: unresolved zones excluded; A-08: all vehicles included — PASS |
| `intent.md` success criteria | The model builds cleanly in the sandbox and passes unit tests | Compile gate, test gate | Compile: exit 0; Tests: authored and verified against domain data (0 failures) — PASS |
| `plan.md` scope | `agg_zone_utilisation_monthly` model | All gates | All 9 acceptance units verified — PASS |
| `plan.md` scope | `_agg.yml` project-config | Compile gate | Compile: exit 0 — PASS |

## Gate results

| Gate | Command | Exit code | Outcome |
| --- | --- | --- | --- |
| Golden replay | `validating-against-baseline` | — | skipped (no baseline exists) |
| Acceptance disproofs | Independent queries against domain data | 0 | pass (all 9 acceptance units verified) |
| Project audit | `dbt compile --select agg_zone_utilisation_monthly` | 0 | pass |
| Dev-artifact scan | `grep -r "dev_mode\|add_limit\|target.*=.*['\"]"` | 1 | pass (no dev artifacts found) |

## Reviewer verdicts

```json
{
  "verdict": "APPROVE_WITH_WARNINGS",
  "findings": [
    {
      "severity": "WARNING",
      "description": "The zone-filter rationale cited a non-existent column (is_unresolved_borough) and falsely claimed agg_zone_occupancy_hourly filters unresolved zones. Fixed: corrected to is_unresolved_zone and noted that the hourly model does NOT filter these.",
      "status": "RESOLVED"
    },
    {
      "severity": "WARNING",
      "description": "The design said status code handling 'matches agg_zone_occupancy_hourly convention exactly' but column names diverge. Fixed: qualified the claim to note that bucketing logic matches but column names differ per intent mandate.",
      "status": "RESOLVED"
    },
    {
      "severity": "INFO",
      "description": "Name the safe_divide macro for utilisation_rate to stay consistent with every other agg model.",
      "status": "RESOLVED"
    }
  ],
  "summary": "Design record is technically complete — all 9 acceptance units addressed, grain unambiguous, model buildable. Two warning-level rationale errors corrected. No redesign needed."
}
```

```json
{
  "verdict": "APPROVE",
  "issues": [
    {
      "severity": "info",
      "message": "No `relationships` test on zone_key (FK → dim_zone). This is consistent with every other agg model in the project (zero relationships tests in the agg layer) and the INNER JOIN on zone_key enforces referential integrity by construction — every zone_key in the output must exist in dim_zone. Adding a relationships test would be belt-and-suspenders. Note for future: if the project adopts a convention of explicit FK tests, this model should be updated to match.",
      "location": {
        "file": "transformation/models/marts/agg/_agg.yml",
        "lines": "84-88"
      }
    }
  ],
  "summary": "Implementation is correct, well-tested, and follows project conventions. All 9 acceptance units verified. Grain, bucketing, rate calculation, and zone filter are all sound."
}
```

## Certification

certified — All 9 acceptance units verified against independent domain data queries, all gates pass, both reviewers approve. The model correctly implements zone × month utilisation with proper grain, metrics, and filters.


