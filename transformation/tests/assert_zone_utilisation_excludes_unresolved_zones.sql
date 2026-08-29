-- Zone utilisation must never include unresolved zones (264 Unknown, 265 N/A).
-- The model filters is_unresolved_zone = false; this asserts the filter holds.
select count(*) as unresolved_zone_rows
from {{ ref('agg_zone_utilisation_monthly') }}
where zone_natural_key in (264, 265)
having count(*) > 0
