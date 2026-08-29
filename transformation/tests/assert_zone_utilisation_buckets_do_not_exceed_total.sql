-- The named buckets (earning + idle + break) cannot exceed total_hours.
-- DISPATCHED, LOGIN, LOGOUT intervals count toward total but have no named bucket,
-- so the sum of named buckets should be <= total. A violation means the bucketing
-- logic is double-counting or misclassifying status codes.
select count(*) as bucket_overflow_rows
from {{ ref('agg_zone_utilisation_monthly') }}
where (earning_hours + idle_hours + break_hours) > (total_hours + 0.001)
having count(*) > 0
