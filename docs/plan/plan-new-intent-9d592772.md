# Plan: Zone by Month Utilisation

`plan.md` carries this intent's own scope and its progress — task checkboxes plus per-task `## Execution evidence` — so nothing here mirrors `intent.md`'s intent approval and design stop, or `verify.md`'s certification, reviewer verdicts, and ship approval. The durable design records say what is true of each artifact across every intent; this file says what *this* intent is doing to them.

> **For agentic workers:** `planning` asks the user to select `subagent-driven-development` (recommended) or `executing-the-plan` (inline) before this plan runs. The choice is not stored here; steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `agg_zone_utilisation_monthly` — a zone × month aggregate showing how much of the time cars in each zone are earning (on trip) versus idle.

**Approach:** Single new model in the `agg` layer, sourcing directly from `fct_status_interval` and `dim_zone`. The aggregation is a single GROUP BY with filtered SUMs for each status code bucket. No intermediate model needed. Follows the pattern of `agg_zone_occupancy_hourly` but at monthly grain with a utilisation focus.

**Tech Stack:** dbt (DuckDB-local), SQL, `safe_divide` macro

## Global Constraints

- Platform: DuckDB-local (from `VD_DOMAIN_DATA_PLATFORM`)
- dbt project: `nyc_taxi_analytics` v2.1.0
- Model path: `transformation/models/marts/agg/agg_zone_utilisation_monthly.sql`
- Materialization: table (per `dbt_project.yml` marts config)
- Schema: `agg` (per `dbt_project.yml`)
- Reporting window: 2024-01-01 to 2024-07-01 (vars `report_start` / `report_end`)
- Naming: `agg_{entity}_{grain}` convention (per AGENTS.md and existing models)
- `safe_divide` macro for null-on-zero division (per `macros/finance.sql`)
- Exclude unresolved zones: `is_unresolved_zone = true` filtered out (A-06)

---

## Scope and impact

What this intent changes. One row per artifact created or changed, linking its durable design record where one applies or stating `code is contract`; `verifying` seeds `## Coverage` from these rows, so an artifact absent here is one nothing will certify.

| Artifact | Kind | Layer | Action | Acceptance units | Design record | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `agg_zone_utilisation_monthly` | model | agg | create | A-01, A-02, A-03, A-04, A-05, A-06, A-07, A-08, A-09 | [`agg_zone_utilisation_monthly.md`](../design/models/agg/agg_zone_utilisation_monthly.md) | Zone × month utilisation aggregate |
| `_agg.yml` | project-config | n/a | modify | A-01 | — code is contract | Add model description and column docs |

**Source mapping.**

| Artifact | Source | Layer hop |
| --- | --- | --- |
| `agg_zone_utilisation_monthly` | `fct_status_interval` (core) + `dim_zone` (core) | core → agg |

**Change impact.**

- **New model:** `agg_zone_utilisation_monthly` — no existing models modified
- **Schema YAML:** `_agg.yml` gets a new model entry — additive, no existing entries changed
- **Downstream consumers:** None yet (new model). Fleet Operations is the intended consumer per CONTEXT.md.
- **No-impact rationale:** This is a greenfield aggregate. No upstream models are modified. No downstream models depend on it yet. The `fct_status_interval` and `dim_zone` sources are read-only.

---

## Tasks

### Task 1: Generate `agg_zone_utilisation_monthly` model SQL

**Acceptance units:** A-01, A-02, A-03, A-04, A-05, A-06, A-07, A-08, A-09

**Files:**

- Create: `transformation/models/marts/agg/agg_zone_utilisation_monthly.sql`

**Steps:**

- [ ] **Step 1: Generate model SQL**

Use `generating-dbt-model` skill to author the model SQL. The model:
- Sources from `{{ ref('fct_status_interval') }}` joined to `{{ ref('dim_zone') }}` on `zone_key` with `is_current_version = true`
- Filters `is_unresolved_zone = false`
- Groups by `zone_key` and `date_trunc('month', interval_date)` as `month_start_date`
- Computes: `total_hours`, `earning_hours` (ON_TRIP), `idle_hours` (AVAILABLE), `break_hours` (BREAK)
- Computes `utilisation_rate` using `{{ safe_divide('earning_hours', 'nullif(total_hours, 0)') }}`
- Passes through zone attributes: `zone_natural_key`, `zone_name`, `borough_name`

- [ ] **Step 2: Add model entry to `_agg.yml`**

Add a model entry with description and column documentation to `transformation/models/marts/agg/_agg.yml`.

- [ ] **Step 3: Sandbox run**

Run: `dbt run --models agg_zone_utilisation_monthly --target-path target`
Expected: exit 0, model materialized in agg schema

- [ ] **Step 4: Commit**

```bash
git add transformation/models/marts/agg/agg_zone_utilisation_monthly.sql transformation/models/marts/agg/_agg.yml
git commit -m "feat: add agg_zone_utilisation_monthly — zone × month utilisation aggregate

- Sources from fct_status_interval + dim_zone (current version)
- Excludes unresolved zones (is_unresolved_zone = true)
- Metrics: total_hours, earning_hours, idle_hours, break_hours, utilisation_rate
- Uses safe_divide macro for null-on-zero consistency
- Closes: A-01 through A-09"
```

### Task 2: Unit tests for `agg_zone_utilisation_monthly`

**Acceptance units:** A-01, A-03, A-04, A-05, A-06

**Files:**

- Create: `transformation/tests/test_agg_zone_utilisation_monthly.sql`

**Steps:**

- [ ] **Step 1: Generate unit tests**

Use `dbt-unit-testing` skill to author tests covering:
- Unique key: `(zone_key, month_start_date)` is unique and not null (A-01)
- Metric correctness: `total_hours` = SUM(interval_seconds)/3600 for all statuses (A-03)
- Metric correctness: `earning_hours` = SUM(interval_seconds)/3600 where ON_TRIP (A-04)
- Ratio correctness: `utilisation_rate` = earning_hours / total_hours, null when total_hours = 0 (A-05)
- Filter correctness: no rows with `is_unresolved_zone = true` (A-06)

- [ ] **Step 2: Run tests**

Run: `dbt test --models agg_zone_utilisation_monthly --target-path target`
Expected: exit 0, all tests pass

- [ ] **Step 3: Commit**

```bash
git add transformation/tests/test_agg_zone_utilisation_monthly.sql
git commit -m "test: add unit tests for agg_zone_utilisation_monthly

- Unique key test on (zone_key, month_start_date)
- Metric correctness tests for total_hours, earning_hours, utilisation_rate
- Filter correctness test for unresolved zone exclusion
- Closes: A-01, A-03, A-04, A-05, A-06"
```

## Execution evidence

Append-only — one line per task, in task order, appended only when that task's checkbox flips (artifact on disk plus a green deterministic gate). Nothing already appended is edited or removed; new evidence only ever adds a line.

Placeholder: `- [x] Task N: <command> — exit 0 — <artifact path> — sha256:<hash>` (a row-hash where a full-file hash is impractical, e.g. one row of a table).

Reviewer verdicts, certification, coverage, Verify gates, and ship approval live in `verify.md`; intent and design-stop approvals live in `intent.md`. This section holds only per-task execution evidence.
