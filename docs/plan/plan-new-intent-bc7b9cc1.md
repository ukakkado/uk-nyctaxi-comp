# Plan: Zone by Month Utilisation

**Goal:** Build `agg_zone_utilisation_monthly` — a zone × month aggregate showing how much time cars earn vs. sit idle in each zone.

**Approach:** One new dbt model in `marts/agg/`, sourcing from `core.fct_status_interval` joined to `core.dim_zone`. The model groups status intervals by zone and month, computing hours by status code (ON_TRIP, AVAILABLE+DISPATCHED, BREAK) and a utilisation rate. No existing models are modified.

**Tech Stack:** dbt-core, DuckDB-local, SQL

## Global Constraints

- Platform: `duckdb_local` (from `VD_DOMAIN_DATA_PLATFORM`)
- dbt project: `nyc_taxi_analytics` v2.1.0
- Report window: `2024-01-01` to `2024-07-01` (vars `report_start` / `report_end`)
- Model naming: `agg_{entity}_{grain}` for aggregate models in `marts/agg/`
- Materialization: `table` (all marts)
- Schema: `agg` (configured in `dbt_project.yml`)
- Macros available: `safe_divide(numerator, denominator)`, `in_report_window(column)`
- Zone resolution: `is_current_version` on `dim_zone`
- No zero-fill: zones with no intervals produce no row

---

## Scope and impact

| Artifact | Kind | Layer | Action | Acceptance units | Design record | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `agg_zone_utilisation_monthly` | model | marts/agg | create | A-01 through A-12 | [`agg_zone_utilisation_monthly.md`](../design/models/agg/agg_zone_utilisation_monthly.md) | Zone × month utilisation from status intervals |

**Source mapping.**

| Source | Layer | Role |
| --- | --- | --- |
| `core.fct_status_interval` | core (mart) | Primary source — status intervals with zone_key, status_code, interval_seconds |
| `core.dim_zone` | core (dimension) | Zone attributes — zone_name, borough_name, is_airport_zone |

**Change impact.**

No existing artifacts impacted — additive build. The model depends on `fct_status_interval` and `dim_zone`, both unchanged. No downstream consumers exist yet.

---

## Tasks

### Task 1: Generate, run, and test `agg_zone_utilisation_monthly`

**Acceptance units:** A-01, A-02, A-03, A-04, A-05, A-06, A-07, A-08, A-09, A-10, A-11, A-12

**Files:**

- Create: `transformation/models/marts/agg/agg_zone_utilisation_monthly.sql`
- Modify: `transformation/models/marts/agg/_agg.yml` (add model description and column tests)
- Test: `transformation/tests/` (unit tests for grain, formula, and consistency)

- [ ] **Step 1: Generate the model SQL**

Invoke `generating-dbt-model` to author `agg_zone_utilisation_monthly.sql` per the design record. The model:
- Sources from `{{ ref('fct_status_interval') }}` joined to `{{ ref('dim_zone') }}` on `zone_key` with `is_current_version`
- Applies `{{ in_report_window('i.interval_date') }}`
- Groups by `date_trunc('month', i.interval_date)` and zone attributes
- Computes: `total_hours`, `on_trip_hours`, `idle_hours` (AVAILABLE + DISPATCHED), `break_hours`, `utilisation_rate`, `distinct_vehicles`, `distinct_drivers`
- Uses `{{ safe_divide('on_trip_hours', 'nullif(total_hours, 0)') }}` for utilisation_rate

- [ ] **Step 2: Add model to `_agg.yml`**

Add a model entry with description and `not_null` test on the grain columns (`month`, `zone_natural_key`).

- [ ] **Step 3: Sandbox run**

Invoke `running-dbt-in-sandbox` to build the model against the ephemeral DuckDB workspace.

Run: `dbt run --select agg_zone_utilisation_monthly`
Expected: exit 0, model materialized in `agg` schema

- [ ] **Step 4: Unit tests**

Invoke `dbt-unit-testing` to author and run tests:
- Grain uniqueness: `count(*) = count(distinct month || '-' || zone_natural_key)`
- Formula check: `utilisation_rate = on_trip_hours / total_hours` for all rows where `total_hours > 0`
- Consistency: `sum(total_hours)` matches `agg_zone_occupancy_hourly` grouped to month (within 0.01 tolerance)
- No zero-fill: no rows where `total_hours = 0`
- Column presence: all 12 columns from design record exist

Run: `dbt test --select agg_zone_utilisation_monthly`
Expected: exit 0, all tests pass

- [ ] **Step 5: Commit**

```bash
git add transformation/models/marts/agg/agg_zone_utilisation_monthly.sql transformation/models/marts/agg/_agg.yml transformation/tests/
git commit -m "feat: agg_zone_utilisation_monthly — zone × month utilisation from status intervals"
```

## Execution evidence

_Pending implementation._
