-- Assert: zone_utilization_rate = on_trip_hours / total_hours (A-08)
-- Returns rows where the rate doesn't match the expected calculation.
-- 0 rows = pass.

select
    month_start_date,
    zone_natural_key,
    total_hours,
    on_trip_hours,
    zone_utilization_rate,
    on_trip_hours / nullif(total_hours, 0) as expected_rate,
    zone_utilization_rate - (on_trip_hours / nullif(total_hours, 0)) as rate_diff
from {{ ref('agg_zone_monthly') }}
where total_hours > 0
  and abs(zone_utilization_rate - (on_trip_hours / nullif(total_hours, 0))) > 0.0001
