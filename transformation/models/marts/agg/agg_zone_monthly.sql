-- Zone × month utilization: how much of the time vehicles spend in each zone
-- is earning (ON_TRIP) versus idle. The monthly counterpart to
-- agg_zone_occupancy_hourly, matching the cadence of agg_vehicle_monthly,
-- agg_driver_monthly, and agg_garage_monthly for the Fleet Operations review.
--
-- Hybrid source (ADR 0003): hours roll up from the hourly aggregate (preserving
-- the pyramid pattern and reconciliation), distinct counts compute from the
-- fact table directly (because count(distinct) cannot be re-aggregated from
-- pre-aggregated hourly values).

with monthly_hours as (
    select
        date_trunc('month', interval_date)                             as month_start_date,
        location_id                                                    as zone_natural_key,
        max(zone_name)                                                 as zone_name,
        max(borough_name)                                              as borough_name,
        max(is_airport_zone)                                           as is_airport_zone,
        coalesce(sum(total_hours), 0)                                  as total_hours,
        coalesce(sum(on_trip_hours), 0)                                as on_trip_hours,
        coalesce(sum(available_hours), 0)                              as available_hours,
        coalesce(sum(break_hours), 0)                                  as break_hours
    from {{ ref('agg_zone_occupancy_hourly') }}
    where {{ in_report_window('interval_date') }}
    group by 1, 2
),

monthly_distinct as (
    select
        date_trunc('month', i.interval_date)                           as month_start_date,
        i.zone_natural_key,
        count(distinct i.driver_key)                                   as distinct_drivers,
        count(distinct i.vehicle_key)                                  as distinct_vehicles
    from {{ ref('fct_status_interval') }} i
    where {{ in_report_window('i.interval_date') }}
      and i.zone_key is not null
    group by 1, 2
)

select
    h.month_start_date,
    h.zone_natural_key,
    h.zone_name,
    h.borough_name,
    h.is_airport_zone,

    h.total_hours,
    h.on_trip_hours,
    h.available_hours,
    h.break_hours,
    h.total_hours - h.on_trip_hours - h.available_hours - h.break_hours   as other_hours,

    d.distinct_drivers,
    d.distinct_vehicles,

    {{ safe_divide('h.on_trip_hours', 'nullif(h.total_hours, 0)') }}      as zone_utilization_rate

from monthly_hours h
join monthly_distinct d
  on h.month_start_date = d.month_start_date
 and h.zone_natural_key = d.zone_natural_key
