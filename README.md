# Harbour Point Taxi Management — analytics warehouse

Brownfield dbt project used as the **fixed Domain** for the contextual-sampling
experiment. Built with no knowledge of any Intent, then frozen.

> **What is real and what is not:** see
> [`docs/data-provenance.md`](docs/data-provenance.md). The TLC trip records are
> genuine NYC open data; the fleet-operations and master-data systems are
> invented. Every dollar in this warehouse is real; every person is not.

## What this is

Harbour Point runs roughly 420 NYC medallions out of six garages. The warehouse
combines three source systems:

| System | Origin | Content |
| --- | --- | --- |
| `bronze` / `silver` | TLC open data, **real** | 20.67M yellow + green trips, Jan–Jun 2024 |
| `ops_raw` | Harbour Point dispatch + telematics, **invented** | 420 vehicles, 760 drivers, 73k shifts, 3.78M status events |
| `mdm_raw` | Master-data platform, **mixed** | Versioned zone and vendor masters, POIs, calendar, weather |

`ops_raw` and `mdm_raw` are generated deterministically from the real trips
(`tools/build_fleet_ops.py`, `tools/build_mdm.py`) — reproducible, internally
consistent, and carrying the imperfections a real feed has.

## Layout

```
CONTEXT.md                domain context and ubiquitous language
docs/data-provenance.md   real TLC data vs generated, tier by tier
docs/intents/             candidate business requests to run through intent capture
docs/adr/                 architecture decisions
tools/                    warehouse builders + local profiling instruments
dbt/models/staging/       20 models, one per source table
dbt/models/intermediate/   7 models, the hard transformations
dbt/models/marts/core/    17 dimensions, bridges and facts
dbt/models/marts/agg/     11 aggregates
dbt/models/marts/finance/  3 marts
dbt/models/marts/ops/      3 marts
```

61 models, 4 seeds, 4 exposures, 8 macros, 143 tests.

## Running it

```bash
python3 tools/build_domain.py       # bronze + silver from raw parquet
python3 tools/build_mdm.py          # master data
python3 tools/build_fleet_ops.py    # fleet operations
cd dbt && DBT_PROFILES_DIR=. dbt build --target domain
```

Raw parquet is not committed. `tools/build_domain.py` expects the TLC files in
`raw/`; fetch them from
<https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page>
(`yellow_tripdata_2024-01..06`, `green_tripdata_2024-01..06`,
`taxi_zone_lookup.csv`).

## Docs

```bash
cd dbt && DBT_PROFILES_DIR=. dbt docs generate --target domain
cd dbt && DBT_PROFILES_DIR=. dbt docs serve --port 8085
```

## Local instruments

```bash
python3 tools/dq.py profile domain.duckdb silver.trips --top 10
python3 tools/dq.py joinev  domain.duckdb silver.trips silver.zones pickup_location_id location_id
python3 tools/dq.py sql     domain.duckdb "select ..."
```

`joinev` emits the six numbers a declared join has to be validated against:
left rows, matched, unmatched, joined rows, distinct keys before and after, and
max matches per left key.
