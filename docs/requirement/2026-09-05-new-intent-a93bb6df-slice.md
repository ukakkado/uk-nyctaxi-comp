# Data slice — Weather dimension on core.fct_trip

Candidate inputs, profiling evidence, and representative-coverage requirements for the two rows in the Deliverables inventory of `2026-09-05-new-intent-a93bb6df.md`.

## 1. `core.dim_weather` (new mart/model)

### Candidate input

`staging.stg_mdm__weather` (view over `mdm_raw.weather_daily`) — already at the target grain, one daily observation per borough, carrying every attribute the dimension needs (`obs_date`, `borough_name`, `temp_avg_f`, `precip_inches`, `snow_inches`, `wind_mph`, `is_wet_day`, `is_snow_day`). No re-aggregation or reshaping required, so the staging contract (`stg_mdm__weather` tests `observation_id` unique/not-null) is the dimension's seed. No join needed.

### Profiling evidence

Read directly from `mdm_raw.weather_daily` (the `staging.stg_mdm__weather` view does not bind in this lakehouse connection — its stored SQL references the `domain` catalog, which is not the default catalog of this connection; the source table resolves and is the same data):

- **Row count:** 1,092 (6 boroughs × 182 days, 2024-01-01 → 2024-06-30)
- **Grain:** `distinct (borough_name, obs_date)` = 1,092 = row count → unique per (borough, date), confirmed
- **Borough set:** Bronx, Brooklyn, EWR, Manhattan, Queens, Staten Island (all with full coverage)
- **Attribute ranges:** `temp_avg_f` 8.1–68.2; `precip_inches` 0–1.41; `snow_inches` 0–6.8; `wind_mph` 3.0–21.0
- **Boundary strata:** 328 wet days (`precip > 0.10`), 37 snow days (`snow > 0.50`); precip and snow both carry exact-zero rows

### Sizing verdict

**Complete table, no sampling** — 1,092 rows is small and already at the target grain. The dimension is the whole weather observation set; the slicing question belongs to the fact join (row 2).

### Join expectations

None — single-table construction.

## 2. `core.fct_trip` (modified mart/model)

### Candidate input

`core.fct_trip` itself (already at the trip grain the row needs), joined with:
- `core.dim_zone` on `fct_trip.pickup_zone_key = dim_zone.zone_key` — supplies the pickup borough **as-of the trip's own date** (the version already resolved by the fact), 
- `core.dim_weather` on `dim_zone.borough_name = dim_weather.borough_name and fct_trip.pickup_date = dim_weather.obs_date` — supplies the single daily observation.

No existing table sits at trip-grain-with-weather; the construction is a many-to-one lookup on top of the fact the request named, so no switch of input.

### Profiling evidence

Trip-side coverage (from `core.fct_trip` × `core.dim_zone` × `mdm_raw.weather_daily`; 1,033,537 trips = 1,033,537 distinct `trip_key`):

| Pickup borough | Trips | With weather row |
| --- | ---: | ---: |
| Manhattan | 914,849 | 914,849 |
| Queens | 96,309 | 96,309 |
| Brooklyn | 15,136 | 15,136 |
| Unknown | 3,270 | 0 |
| Bronx | 3,175 | 3,175 |
| N/A | 618 | 0 |
| EWR | 141 | 141 |
| Staten Island | 37 | 37 |

- **Resolvable:** 1,029,649 trips (99.6%) match exactly one weather row on `(borough, pickup_date)`.
- **Unresolvable:** 3,888 trips (0.4%) in the `Unknown`/`N/A` boroughs — no weather row exists for those borough names, by construction of the source data; these must carry a null `weather_key` and remain in the fact.
- Weather coverage spans the whole reporting window, so the only in-window non-matches are the `Unknown`/`N/A` boroughs.

### Sizing verdict

Fact-side validation uses a **stratified slice**, not the full 1.03M-trip scan, on every build round. The strata must cover every join-relevant class and boundary:

- all 8 pickup borough values present in `dim_zone` (every weather borough + `Unknown` and `N/A` for the null-key path),
- boundary weather days: min/max `temp_avg_f`, `precip_inches` exactly 0 and > 0.10, `snow_inches` exactly 0 and > 0.50,
- at least one trip per month of the reporting window.

Bounded export SQL (shape, not a fixed row cap): the union of
`select f.*, z.borough_name, w.observation_id as weather_key from core.fct_trip f join core.dim_zone z on f.pickup_zone_key = z.zone_key left join mdm_raw.weather_daily w on w.borough_name = z.borough_name and w.obs_date = f.pickup_date`
restricted to (a) every trip whose pickup borough is in any non-dominant class (`Bronx`, `Brooklyn`, `EWR`, `Staten Island`, `Unknown`, `N/A`), taken in full, plus (b) a cap on the dominant `Manhattan`/`Queens` case on the boundary dates in the strata above. Once the models exist, the same shape runs against `core.dim_weather` (keyed by `weather_key`) and the built `core.fct_trip`.

### Join expectations

- `fct_trip → dim_zone` (as-of pickup version): **mandatory many-to-one** — existing production join in `fct_trip`; the row-count assertion `assert_fct_trip_matches_silver_rowcount` already depends on it.
- `fct_trip → dim_weather` on `(borough, obs_date)`: **optional many-to-one at the trip level** (null for unresolvable trips) and strictly one-to-one from the weather side — `(borough, obs_date)` is unique in the source (grain confirmed above), so the left join cannot fan out. This is a **new join**; its many-to-one property is validated above from source grain, not assumed.

## Notes

- One environment quirk worth recording: the domain lakehouse connection's default catalog is not named `domain`, so dbt views whose stored SQL references the `domain.` catalog (e.g. `staging.stg_mdm__weather`) fail to bind here. Read the underlying source tables (`mdm_raw.*`) directly for evidence. This changes nothing about the artifact or acceptance units.
- All slice findings agree with `intent.md`; no resolved grain, filter, or key is contradicted, so nothing returns to `capturing-intent`.