# Data Slice: Zone by Month Utilization

## Deliverable: `agg.agg_zone_monthly`

### Candidate input

**Primary:** `agg.agg_zone_occupancy_hourly` — zone × hour grain, one level below the target zone × month grain. Already carries `total_hours`, `on_trip_hours`, `available_hours`, `break_hours`, `distinct_drivers`, `distinct_vehicles`, and zone attributes (`zone_natural_key`, `zone_name`, `borough_name`, `is_airport_zone`). Rolling this to month is a straightforward `date_trunc` + `group by`.

**Why not `core.fct_status_interval` directly?** The hourly aggregate already performs the zone join, daypart mapping, and status-code bucketing. Building from it follows the pyramid pattern (each level built from the one below: `fct_status_interval` → `agg_zone_occupancy_hourly` → `agg_zone_monthly`), ensuring the monthly numbers reconcile with the hourly ones. Going back to the fact table would duplicate logic and risk divergence.

**Dimension join:** `core.dim_zone` is already joined in the hourly model and its attributes are carried through. No additional dimension join is needed unless the monthly model wants zone attributes not present in the hourly output (e.g., `demand_tier`, `area_sq_mi`). Following the hourly model's pattern: carry `zone_natural_key`, `zone_name`, `borough_name`, `is_airport_zone`.

### Profiling evidence

**`agg.agg_zone_occupancy_hourly`:**
- Row count: 83,342
- Distinct zones: 245
- Date range: 2024-01-01 to 2024-07-01 (reporting window)
- Rows per month: ~12,400–14,960 (July 2024 has only 3 rows — boundary effect)
- Size: small enough to scan completely on every build; no sampling needed

**`core.fct_status_interval` status code distribution:**
- AVAILABLE: 109,393 intervals, 31,567 hours
- BREAK: 9,679 intervals, 23,943 hours
- DISPATCHED: 60,075 intervals, 3,001 hours
- LOGIN: 49,318 intervals, 822 hours
- LOGOUT: 48,529 intervals, 0 hours
- ON_TRIP: 60,075 intervals, 16,160 hours

**Key finding:** The hourly model buckets only three statuses (ON_TRIP, AVAILABLE, BREAK). The remaining statuses (DISPATCHED, LOGIN, LOGOUT) contribute to `total_hours` but are not named in any bucket. The monthly model must account for this: `other_hours = total_hours - on_trip_hours - available_hours - break_hours` captures the gap.

### Sizing verdict

**Bring the complete table.** At 83K rows, `agg_zone_occupancy_hourly` is small. No sampling. The monthly rollup will produce approximately 245 zones × 6 months = ~1,470 rows.

### Join expectations

**`agg_zone_occupancy_hourly` → `dim_zone`:** Already joined in the hourly model on `zone_key` (surrogate key). The hourly model uses `is_current_version` implicitly through the surrogate key join. The monthly model inherits this; no new join is introduced.

**Expected cardinality:** Many-to-one (many hourly rows per zone-month → one monthly row per zone). The grain key is `(zone_natural_key, month_start_date)`.

### Bounded export SQL (shape)

```sql
select
    date_trunc('month', interval_date) as month_start_date,
    zone_natural_key,
    zone_name,
    borough_name,
    is_airport_zone,
    sum(total_hours) as total_hours,
    sum(on_trip_hours) as on_trip_hours,
    sum(available_hours) as available_hours,
    sum(break_hours) as break_hours,
    sum(total_hours) - sum(on_trip_hours) - sum(available_hours) - sum(break_hours) as other_hours,
    count(distinct distinct_drivers) as distinct_drivers,
    count(distinct distinct_vehicles) as distinct_vehicles,
    case when sum(total_hours) > 0 
         then sum(on_trip_hours) / sum(total_hours) 
         else null end as zone_utilization_rate
from agg.agg_zone_occupancy_hourly
where interval_date >= timestamp '2024-01-01'
  and interval_date < timestamp '2024-07-01'
group by 1, 2, 3, 4, 5
order by 1, 2
```

**Note on distinct counts:** The hourly model carries `distinct_drivers` and `distinct_vehicles` as pre-aggregated counts. Summing or averaging these across hours would be incorrect. The monthly model must re-aggregate from the underlying fact table to get correct distinct counts, or accept that the hourly distinct counts are lower bounds. **Decision:** Re-aggregate from `core.fct_status_interval` for `distinct_drivers` and `distinct_vehicles` to ensure correctness. This is a deviation from the "build from hourly" pattern, justified by the fact that distinct counts cannot be safely re-aggregated from pre-aggregated values.

**Revised candidate input:** Hybrid approach — roll up hours from `agg_zone_occupancy_hourly`, but compute distinct counts from `core.fct_status_interval` directly. This ensures hour reconciliation (A-14) and correct distinct counts (A-09, A-10).
