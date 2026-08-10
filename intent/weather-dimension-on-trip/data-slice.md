# Intent Data Slice: Weather dimension on fct_trip (R9)

Companion to `intent.md`, per the
[Contextual Sampling proposal](https://github.com/accelerate-data/studio/blob/main/docs/proposals/contextual-sampling/README.md).

## 1. Model inventory

| Model | Grain | Purpose |
| --- | --- | --- |
| `dim_weather` | one row per (`obs_date`, `borough_name`) | New Type 1 weather dimension |
| `fct_trip` (edit) | unchanged, one row per `trip_key` | Add `weather_key` FK |

## 2. Candidate inputs

- `mdm_raw.weather_daily` / `stg_mdm__weather` — for `dim_weather`.
- `core.fct_trip` + `core.dim_zone` — for resolving `weather_key` on the
  existing fact.

## 3. Profiling evidence

| Probe | Result |
| --- | --- |
| `weather_daily` row count | 1,092 = exactly 6 boroughs x 182 days, no gaps |
| `obs_date` range | 2024-01-01 to 2024-06-30 — matches the reporting window exactly |
| Boroughs in `weather_daily` | Bronx, Brooklyn, EWR, Manhattan, Queens, Staten Island |
| Boroughs in `dim_zone` | same 6, plus `Unknown` and `N/A` |

`dim_zone`'s two extra boroughs will never match a weather row — exactly the
expected null case the intent already anticipates.

**Adequacy verdict: Ready.**

## 4. Representative coverage requirement

**`dim_weather`:** bring the complete table as-is. 1,092 rows is trivially
small and already at the target grain with no gaps to sample around.

**`fct_trip.weather_key` resolution:** doesn't need a large slice of
`fct_trip` to validate the join logic — a small, deliberate set is enough:

- several trips per borough (all 6 weather-covered boroughs), across a few
  different `obs_date`s, to prove `weather_key` resolves per (date, borough);
- at least one trip whose pickup zone is `'Unknown'` or `'N/A'`, to prove
  `weather_key` comes back null rather than mismatched to another borough's
  weather;
- at least one trip on 2024-01-01 and one on 2024-06-30 — the boundary dates
  of `weather_daily`'s coverage — to catch an off-by-one on the date range.

## 5. Join validation

`fct_trip` → `dim_zone` (existing, unmodified) to get `borough_name`, then
`borough_name` + `pickup_date` → `dim_weather` — a genuine many-to-one (many
trips per borough-day, one weather observation), mirroring
`agg_weather_demand_daily`'s existing production join. Any unmatched trip
should be exactly the `'Unknown'`/`'N/A'` population and nothing else.

## 6. Bounded export definition

```sql
-- dim_weather: whole table
select * from mdm_raw.weather_daily;

-- fct_trip sample for weather_key validation
select f.*
from core.fct_trip f
join core.dim_zone z on f.pickup_zone_key = z.zone_key
where z.borough_name in
  ('Bronx','Brooklyn','EWR','Manhattan','Queens','Staten Island','Unknown','N/A')
-- a handful of trips per borough per a few sampled dates, plus explicit
-- inclusion of the 2024-01-01 / 2024-06-30 boundary dates
```

## 7. Business ambiguity resolved with the user

None — the null-for-unresolved-borough behavior follows the domain's existing
convention directly (`is_fleet_attributed`'s precedent).
