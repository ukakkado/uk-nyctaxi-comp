# Harbour Point Taxi Management — analytics warehouse

Brownfield dbt project used as the **fixed Domain** for the contextual-sampling
experiment. Built with no knowledge of any Intent, then frozen.

## What this is

Harbour Point runs roughly 420 NYC medallions out of six garages. The warehouse
combines three source systems:

| System | Origin | Content |
| --- | --- | --- |
| `bronze` / `silver` | TLC open data, **real** | 20.67M yellow + green trips, Jan-Jun 2024 |
| `ops_raw` | Harbour Point dispatch + telematics | 420 vehicles, 760 drivers, 73k shifts, 3.78M status events |
| `mdm_raw` | Master-data platform | Versioned zone and vendor masters, POIs, calendar, weather |

`ops_raw` and `mdm_raw` are generated deterministically from the real trips
(`tools/build_fleet_ops.py`, `tools/build_mdm.py`) — reproducible, internally
consistent, and carrying the imperfections a real feed has.

## Layout

```
tools/                 warehouse builders + local profiling instruments
dbt/models/staging/    20 models, one per source table
dbt/models/intermediate/  7 models, the hard transformations
dbt/models/marts/core/    17 dimensions, bridges and facts
dbt/models/marts/agg/     11 aggregates
dbt/models/marts/finance/  3 marts
dbt/models/marts/ops/      3 marts
```

## Running it

```bash
python3 tools/build_domain.py       # bronze + silver from raw parquet
python3 tools/build_mdm.py          # master data
python3 tools/build_fleet_ops.py    # fleet operations
cd dbt && DBT_PROFILES_DIR=. dbt build --target domain
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
