# Sample NYC Taxi Analytics Domain

An intentionally brownfield DuckDB + dbt warehouse for NYC taxi analytics and
intent-driven data work. It combines genuine NYC TLC trip records with
deterministically generated fleet-operations and master-data systems.

The project tests joins, sessionization, SCD2 dimensions, quality rules, and
aggregate design without pretending that generated driver, vehicle, garage, or
weather data is real.

## Data provenance

| Layer | Contents | Provenance |
| --- | --- | --- |
| `bronze` | Yellow/Green trips and TLC zone lookup | Trips are landed from official TLC Parquet files; the zone lookup is CSV. Source columns are preserved and ingestion metadata is added. |
| `silver` | Conformed trips, zones, payment types, and rate codes | Derived from Bronze; Yellow and Green are unioned, renamed, keyed, and deduplicated. |
| `ops_raw` | Garages, vehicles, drivers, leases, shifts, assignments, status events, maintenance | Fully synthetic and deterministic, generated from landed TLC trips. |
| `mdm_raw` | Zone/vendor/payment/rate/borough/calendar/POI/weather data | Mixed: some labels/rates are hand-transcribed; enriched attributes and weather are generated. |
| dbt models | Staging, intermediate, dimensions, facts, marts, and aggregates | Derived transformations and business rules. |

The TLC trip window is January–June 2024. Read the full tier-by-tier notes in
[`docs/data-provenance.md`](docs/data-provenance.md) before treating a result
as a real-world claim. Trip-level TLC facts are genuine; Harbour Point
identities and operational outcomes are not.

## Architecture

```text
official TLC Parquet + CSV
          │
          ▼
tools/download_bronze_data.py
          │
          ▼
tools/build_domain.py ─────► bronze ─────► silver
          │                                      │
          ├── tools/build_mdm.py ───────► mdm_raw
          └── tools/build_fleet_ops.py ──► ops_raw
                                                 │
                                                 ▼
                              dbt build: staging → intermediate → marts
                                                 │
                                                 ▼
                                      dbt docs generate
```

`domain.duckdb`, downloaded source files, and transformation artifacts are ignored by Git.
A complete rebuild is reproducible from the scripts and public TLC inputs
without committing a multi-gigabyte warehouse.

## Repository layout

- `CONTEXT.md`: domain context and analytical vocabulary.
- `docs/data-provenance.md`: real versus generated data, tier by tier.
- `docs/adr/`: architecture decisions.
- `docs/intents/` and `intent/`: candidate business requests and data slices.
- `transformation/models/staging/`: source-shaped views.
- `transformation/models/intermediate/`: conformance and hard transformations.
- `transformation/models/marts/`: core dimensions/facts, aggregates, finance, and operations.
- `transformation/seeds/`: analyst-owned daypart, distance, duration, and fare bands.
- `tools/download_bronze_data.py`: download official TLC inputs.
- `tools/build_domain.py`: build the Bronze/Silver baseline.
- `tools/build_mdm.py`: build deterministic MDM source data.
- `tools/build_fleet_ops.py`: build deterministic fleet source data.
- `tools/build_synthetic_sources.py`: run the two generated source builders.
- `tools/build_dbt_and_docs.py`: run dbt and generate documentation.
- `tools/dq.py`: local profiling and join-evidence utility.

## Prerequisites

- Python 3.9 or newer
- DuckDB Python package
- dbt Core with the DuckDB adapter
- Internet access for the TLC downloads

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install duckdb dbt-core dbt-duckdb
```

## Full rebuild

Run from the repository root:

```bash
# Download Yellow/Green trip Parquet and the TLC zone lookup into raw/.
python3 tools/download_bronze_data.py

# Recreate domain.duckdb. This replaces the local database if it exists.
python3 tools/build_domain.py

# Add the generated MDM and fleet-operations source systems.
python3 tools/build_synthetic_sources.py

# Build all dbt models, run tests, and generate the docs site.
python3 tools/build_dbt_and_docs.py
```

`build_dbt_and_docs.py` is the named entry point for the dbt layer: it runs
`dbt build`, then `dbt docs generate`, and writes the documentation artifacts
under `transformation/target/`.

### Individual commands

Download selected files:

```bash
python3 tools/download_bronze_data.py \
  --months 2024-01 2024-02 2024-03 \
  --fleet yellow
```

Build source systems independently:

```bash
python3 tools/build_domain.py
python3 tools/build_mdm.py
python3 tools/build_fleet_ops.py

# Or run the generated systems together after the domain exists.
python3 tools/build_synthetic_sources.py
python3 tools/build_synthetic_sources.py --only mdm
python3 tools/build_synthetic_sources.py --only fleet
```

Run dbt or regenerate documentation from an existing build:

```bash
python3 tools/build_dbt_and_docs.py --target domain
python3 tools/build_dbt_and_docs.py --target domain --docs-only
```

The equivalent direct commands are:

```bash
cd transformation
DBT_PROFILES_DIR=. dbt build --target domain
DBT_PROFILES_DIR=. dbt docs generate --target domain
DBT_PROFILES_DIR=. dbt docs serve --port 8085
```

Open <http://localhost:8085> after starting the docs server.

## dbt targets and model layers

`transformation/profiles.yml` defines `domain` (`../domain.duckdb`) and `slice`
(`../slice.duckdb`) targets. The project is organized as:

- **staging**: source-shaped views over `bronze`, `silver`, `ops_raw`, and `mdm_raw`.
- **intermediate**: conformed trip, status, occupancy, fare, and quality logic.
- **core marts**: dimensions, bridges, and facts.
- **aggregates**: driver, vehicle, zone, OD, weather, and occupancy summaries.
- **finance marts**: daily revenue, monthly summaries, and revenue bridges.
- **operations marts**: driver, vehicle, and trip-quality scorecards.
- **seeds**: four analyst-owned banding tables.

The reporting window (`2024-01-01` through `2024-07-01`) and billable-trip
definition live in dbt models and project variables. They are not applied when
Bronze or Silver is built.

## Validation and exploration

```bash
python3 tools/dq.py profile domain.duckdb silver.trips --top 10
python3 tools/dq.py joinev domain.duckdb \
  silver.trips silver.zones pickup_location_id location_id
python3 tools/dq.py sql domain.duckdb \
  "select service_type, count(*) from silver.trips group by 1"
```

`dbt build` runs tests for trip row-count reconciliation, airport fee rules,
status interval validity, SCD2 zone overlap, and shift-time reconciliation.

## Important limitations

- Do not commit `domain.duckdb`, Parquet files, CSV downloads, `transformation/target/`, or
  `transformation/logs/`; they are covered by `.gitignore`.
- `ops_raw` driver, vehicle, garage, lease, maintenance, and weather records
  are synthetic and are not real NYC operations.
- Generated zone coordinates, population, area, demand tiers, and version
  histories are plausible-looking test attributes, not authoritative geography.
- Re-running `tools/build_domain.py` replaces the local DuckDB file.

## Source and license

Trip records and the zone lookup are downloaded from the official NYC Taxi &
Limousine Commission trip-record-data page:
<https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page>

Check the source terms and attribution requirements before redistributing the
downloaded data. This repository publishes build logic and metadata; the large
source files are intentionally not published with it.
