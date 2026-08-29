-- utilisation_rate = earning_hours / total_hours. It must be in [0, 1] or null
-- when total_hours is zero. A value outside this range means the ratio formula
-- is wrong or the numerator/denominator are misaligned.
select count(*) as invalid_utilisation_rate_rows
from {{ ref('agg_zone_utilisation_monthly') }}
where utilisation_rate is not null
  and (utilisation_rate < 0 or utilisation_rate > 1.001)
having count(*) > 0
