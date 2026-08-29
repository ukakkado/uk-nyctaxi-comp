# uk-nyctaxi-comp Data Product

**Owner:** {Team Name}
**Sources:** {Salesforce | QuickBooks | PostgreSQL | etc.}
**Refresh:** {Daily at 6 AM UTC | Hourly | Real-time}

---

## Medallion Layers

### Staging (Bronze → Silver)

- **Naming:** `stg_{source}__{table}`
- **Materialization:** Views
- **Purpose:** 1:1 with source tables, rename columns, filter soft-deletes

### Marts (Silver → Gold)

- **Naming:** `fct_{process}` or `dim_{entity}`
- **Materialization:** Tables
- **Purpose:** Business logic, star schema, aggregations

### Semantic

- **Naming:** `{domain}_metrics.yml`
- **Purpose:** Metric definitions for consistency

---

## Naming Conventions

| Type            | Pattern                 | Example                       |
| --------------- | ----------------------- | ----------------------------- |
| Staging model   | `stg_{source}__{table}` | `stg_salesforce__opportunity` |
| Fact table      | `fct_{process}`         | `fct_pipeline_daily`          |
| Dimension table | `dim_{entity}`          | `dim_account`                 |
| Primary key     | `{entity}_id`           | `opportunity_id`              |
| Date column     | `{event}_date`          | `close_date`                  |
| Boolean column  | `is_{condition}`        | `is_closed_won`               |
| Amount column   | `{metric}_amount`       | `total_amount`                |

---

## Business Rules

### {Rule 1 Name}

{Brief description}

```sql
-- Example SQL
WHERE is_deleted = FALSE
  AND amount > 0
```

### {Rule 2 Name}

{Brief description}

```sql
-- Example SQL
CASE
  WHEN stage_name = 'Closed Won' AND is_closed = TRUE THEN TRUE
  ELSE FALSE
END AS is_closed_won
```

---

## Validation Standards

**Tolerance:**

- Row count: ±2% acceptable, ±10% fails build
- Currency amounts: ±$1,000 or 1% acceptable, ±5% fails build

**Required Tests:**

- `not_null` on all primary keys
- `unique` on all primary keys
- `relationships` on all foreign keys

---

## Fabric Configuration

- **Workspace:** UK-NYCTAXI-COMP\_MAIN
- **Lakehouse:** UK-NYCTAXI-COMP\_LH
- **Schema:** dbo
- **Ephemeral Prefix:** {domain}_fb_

---

## Artifact Paths

Where the agents write what they author in this repo. Every row has a working default — edit a path to override it, delete a row to accept the default, delete the whole table to accept all of them. A path is created on first write, never scaffolded up front.

| Artifact            | Path                                       |
| ------------------- | ------------------------------------------ |
| Requirement         | `docs/requirements/reqt-{intent-slug}.md`  |
| Data slice          | `docs/requirements/slice-{intent-slug}.md` |
| Intent design       | `docs/design/design-{intent-slug}.md`      |
| Model design        | `docs/design/{model}.md`                   |
| Implementation plan | `docs/plan/plan-{intent-slug}.md`          |
| Certification       | `docs/verify/verify-{intent-slug}.md`      |

Design is two files. The **intent design** records what one intent decided and is finished when it ships. A **model design** is one file per model, amended by each later intent that changes it, so the record follows the model rather than the work that created it.

Declared elsewhere, and not overridable here:

| Artifact                                              | Declared in                                                                                       |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| Generated dbt models, tests, macros, snapshots, seeds | `transformation/dbt_project.yml` — dbt resolves these itself, so a path set here would be ignored |
| dlt pipelines, connectors, resource docs              | fixed by the dlt project layout under `ingestion/`                                                |
| Glossary                                              | `CONTEXT.md`, repo root                                                                           |
| Architectural decisions                               | `docs/adr/NNNN-{slug}.md`                                                                         |

---

## Context & Decision Memory Precedence

This repo's own `CONTEXT.md` (root) and `docs/adr/` are durable, committed memory: the
ubiquitous language and past architectural decisions the agents building, fixing, and
advising on this domain's data products rely on across intents. When a source of truth
conflicts with another, resolve it in this order, most specific first:

1. **The current intent's own `intent/<slug>/design.md`** — the in-flight record for the
   work happening right now; it can temporarily diverge from a stale ADR until that ADR is
   reconciled.
2. **This repo's own `CONTEXT.md` and `docs/adr/`** — durable, cross-intent, committed.
3. **The agent runtime's own ephemeral working memory** (not committed to this repo) —
   fills gaps the two sources above don't cover, but never overrides a documented
   convention or an accepted decision.

Neither `CONTEXT.md` nor `docs/adr/` ever holds an example value, identifier, or row
content seen in conversation — only structural facts (a term's meaning, a decision and its
reasoning).
