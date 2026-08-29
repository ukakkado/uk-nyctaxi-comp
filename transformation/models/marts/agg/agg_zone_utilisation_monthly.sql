-- Zone × month utilisation: how much of the time cars spend in a zone is spent
-- actually earning (on a trip) versus sitting idle or on break.
--
-- Source: fct_status_interval (one row per driver-vehicle state interval).
-- Grain: one row per (zone_key, month_start_date).
-- Status codes: ON_TRIP = earning, AVAILABLE = idle, BREAK = break.
-- DISPATCHED, LOGIN, LOGOUT count toward total_hours but have no named bucket.
-- Unresolved zones (264 Unknown, 265 N/A) are excluded.
select
    si.zone_key,
    cast(date_trunc('month', si.interval_date) as date)               as month_start_date,

    -- Zone attributes (from current version of dim_zone)
    z.zone_natural_key,
    z.zone_name,
    z.borough_name,

    -- Hour buckets by status code
    sum(si.interval_seconds) / 3600.0                                  as total_hours,
    coalesce(sum(si.interval_seconds) filter (where si.status_code = 'ON_TRIP'), 0) / 3600.0    as earning_hours,
    coalesce(sum(si.interval_seconds) filter (where si.status_code = 'AVAILABLE'), 0) / 3600.0  as idle_hours,
    coalesce(sum(si.interval_seconds) filter (where si.status_code = 'BREAK'), 0) / 3600.0      as break_hours,

    -- Utilisation rate: earning hours / total hours, null when total is zero
    {{ safe_divide(
        "coalesce(sum(si.interval_seconds) filter (where si.status_code = 'ON_TRIP'), 0)::double",
        "nullif(sum(si.interval_seconds), 0)::double"
    ) }}                                                               as utilisation_rate

from {{ ref('fct_status_interval') }} si
join {{ ref('dim_zone') }} z
    on si.zone_key = z.zone_key
    and z.is_current_version = true
where z.is_unresolved_zone = false
group by 1, 2, 3, 4, 5
