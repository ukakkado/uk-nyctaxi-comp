-- Assert: monthly hours reconcile with hourly aggregate (A-14)
-- Monthly totals must equal the sum of hourly totals for the same zone and month.
-- Returns rows where reconciliation fails (0 rows = pass).

with monthly_from_model as (
    select
        month_start_date,
        zone_natural_key,
        total_hours,
        on_trip_hours,
        available_hours,
        break_hours
    from {{ ref('agg_zone_monthly') }}
),

monthly_from_hourly as (
    select
        date_trunc('month', interval_date) as month_start_date,
        location_id as zone_natural_key,
        coalesce(sum(total_hours), 0) as total_hours,
        coalesce(sum(on_trip_hours), 0) as on_trip_hours,
        coalesce(sum(available_hours), 0) as available_hours,
        coalesce(sum(break_hours), 0) as break_hours
    from {{ ref('agg_zone_occupancy_hourly') }}
    where {{ in_report_window('interval_date') }}
    group by 1, 2
)

select
    m.month_start_date,
    m.zone_natural_key,
    m.total_hours as model_total_hours,
    h.total_hours as hourly_total_hours,
    m.total_hours - h.total_hours as total_hours_diff,
    m.on_trip_hours as model_on_trip_hours,
    h.on_trip_hours as hourly_on_trip_hours,
    m.on_trip_hours - h.on_trip_hours as on_trip_hours_diff
from monthly_from_model m
full outer join monthly_from_hourly h
  on m.month_start_date = h.month_start_date
 and m.zone_natural_key = h.zone_natural_key
where abs(coalesce(m.total_hours, 0) - coalesce(h.total_hours, 0)) > 0.001
   or abs(coalesce(m.on_trip_hours, 0) - coalesce(h.on_trip_hours, 0)) > 0.001
   or abs(coalesce(m.available_hours, 0) - coalesce(h.available_hours, 0)) > 0.001
   or abs(coalesce(m.break_hours, 0) - coalesce(h.break_hours, 0)) > 0.001
   or m.month_start_date is null
   or h.month_start_date is null
