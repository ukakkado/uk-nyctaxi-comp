# Plan: Zone by Month Utilization

`plan.md` carries this intent's own scope and its progress — task checkboxes plus per-task `## Execution evidence` — so nothing here mirrors `intent.md`'s intent approval and design stop, or `verify.md`'s certification, reviewer verdicts, and ship approval. The durable design records say what is true of each artifact across every intent; this file says what *this* intent is doing to them.

> **For agentic workers:** `planning` asks the user to select `subagent-driven-development` (recommended) or `executing-the-plan` (inline) before this plan runs. The choice is not stored here; steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `agg.agg_zone_monthly`, a zone × month utilization aggregate showing how much time vehicles spend earning vs. idle in each zone.

**Approach:** Hybrid source — hours roll up from `agg_zone_occupancy_hourly` (preserving the pyramid pattern and reconciliation), distinct counts compute from `fct_status_interval` (because distinct counts cannot be re-aggregated). The two branches join on `(zone_natural_key, month_start_date)`. Durable decisions live in [`docs/design/models/agg/agg_zone_monthly.md`](../design/models/agg/agg_zone_monthly.md) and [ADR 0003](../adr/0003-hybrid-source-for-monthly-distinct-counts.md).

**Tech Stack:** dbt 1.12.3, DuckDB 1.11.0, DuckDB-local ephemeral workspace

## Global Constraints

- Platform: DuckDB-local (`VD_DOMAIN_DATA_PLATFORM=duckdb_local`)
- dbt version: 1.12.3, duckdb adapter 1.11.0
- Reporting window: `report_start = '2024-01-01'`, `report_end = '2024-07-01'` (vars in `dbt_project.yml`)
- Naming convention: `agg_{entity}_{grain}` for aggregates (e.g., `agg_vehicle_monthly`, `agg_driver_monthly`)
- Materialization: table in `agg` schema (configured in `dbt_project.yml`)
- Use `safe_divide` macro for null-safe division
- Use `in_report_window` macro for reporting window filter
- All zones included (no unresolved-zone filter) — `dim_zone.is_unresolved_zone` available for consumers

---

## Scope and impact

| Artifact | Kind | Layer | Action | Acceptance units | Design record | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `agg_zone_monthly` | model | agg (mart) | create | A-01 through A-14 | [`agg_zone_monthly.md`](../design/models/agg/agg_zone_monthly.md) | Zone × month utilization aggregate |

**Source mapping.**

- `agg.agg_zone_occupancy_hourly` → hours (total, on_trip, available, break), zone attributes
- `core.fct_status_interval` → distinct_drivers, distinct_vehicles
- `core.dim_zone` → zone attributes (via hourly model)

**Change impact.**

No existing artifacts impacted — fresh build target. `agg_zone_monthly` is a new leaf node with no downstream consumers. It reads from existing models (`agg_zone_occupancy_hourly`, `fct_status_interval`, `dim_zone`) but does not modify them.

---

## Tasks

### Task 1: Generate `agg_zone_monthly` model

**Acceptance units:** A-01, A-02, A-03, A-04, A-05, A-06, A-07, A-08, A-09, A-10, A-11, A-12, A-13, A-14

**Files:**

- Create: `transformation/models/marts/agg/agg_zone_monthly.sql`
- Modify: `transformation/models/marts/agg/_agg.yml` (add model entry and column descriptions)

- [ ] **Step 1: Generate the model SQL**

Invoke `generating-dbt-model` skill with:
- Artifact kind: model
- Layer: agg (mart)
- Grain: `(zone_natural_key, month_start_date)`
- Design record: `docs/design/models/agg/agg_zone_monthly.md`
- Acceptance units: A-01 through A-13

The skill will author the SQL following the hybrid source pattern:
- Branch 1: Roll up hours from `agg_zone_occupancy_hourly` grouped by `(zone_natural_key, date_trunc('month', interval_date))`
- Branch 2: Compute distinct counts from `fct_status_interval` with the same grain and zone filter
- Join branches on `(zone_natural_key, month_start_date)`
- Apply `in_report_window` filter
- Compute `zone_utilization_rate` using `safe_divide`

- [ ] **Step 2: Add model entry to `_agg.yml`**

Add model entry with description and column descriptions following the pattern in `_agg.yml`. Include:
- Model description explaining the hybrid source and utilization concept
- Column descriptions for all 12 columns
- Primary key test on `(zone_natural_key, month_start_date)`

- [ ] **Step 3: Run the model in the sandbox**

Invoke `running-dbt-in-sandbox` skill to build the model against the ephemeral DuckDB workspace.

Run: `dbt run --select agg_zone_monthly --target-path target`
Expected: exit 0, model materialized in `agg` schema

- [ ] **Step 4: Run unit tests**

Invoke `dbt-unit-testing` skill to generate and run unit tests for the model.

Tests should cover:
- Grain uniqueness (A-01)
- Hour reconciliation with hourly model (A-14)
- Distinct count correctness (A-09, A-10)
- Utilization rate calculation (A-08)
- Reporting window filter (A-12)

Run: `dbt test --select agg_zone_monthly`
Expected: exit 0, all tests pass

- [ ] **Step 5: Commit**

```bash
git add transformation/models/marts/agg/agg_zone_monthly.sql transformation/models/marts/agg/_agg.yml
git commit -m "Build agg_zone_monthly: zone × month utilization aggregate

- Hybrid source: hours from hourly aggregate, distinct counts from fact table
- Follows ADR 0003 (hybrid source pattern for monthly aggregates)
- Acceptance units A-01 through A-14"
```

---

## Execution evidence

Append-only — one line per task, in task order, appended only when that task's checkbox flips (artifact on disk plus a green deterministic gate). Nothing already appended is edited or removed; new evidence only ever adds a line.

Placeholder: `- [x] Task N: <command> — exit 0 — <artifact path> — sha256:<hash>` (a row-hash where a full-file hash is impractical, e.g. one row of a table).

Reviewer verdicts, certification, coverage, Verify gates, and ship approval live in `verify.md`; intent and design-stop approvals live in `intent.md`. This section holds only per-task execution evidence.
