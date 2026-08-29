# Data Slice: Zone by Month Utilisation

## Deliverable: `agg_zone_utilisation_monthly`

### Candidate input

`core.fct_status_interval` joined to `core.dim_zone` on `zone_key`.

This is the same construction `agg_zone_occupancy_hourly` uses. The hourly model is at a finer grain than needed; rolling it to month would work but loses the status-code breakdown the monthly model needs (idle vs. break vs. earning). Going directly to `fct_status_interval` preserves the status_code column without an extra aggregation step.

### Profiling evidence

**fct_status_interval (full table):**

| Metric | Value |
| --- | --- |
| Total rows | 337,069 |
| Rows with resolved zone_key | 189,904 (56.4%) |
| Rows with null zone_key | 147,165 (43.6%) — LOGIN, LOGOUT, and pre-zone AVAILABLE intervals |
| Distinct zones | 245 |
| Distinct vehicles | 420 |
| Distinct drivers | 760 |
| Date range | 2023-12-31 to 2024-07-01 |
| Distinct months | 8 (Dec 2023 has 15 rows / 0 zones; Jul 2024 has 6 rows / 3 zones) |

**Status code distribution (zone-resolved rows only):**

| status_code | rows | hours | zones |
| --- | --- | --- | --- |
| AVAILABLE | 60,075 | ~16,200 | 229 |
| ON_TRIP | 60,075 | 16,160 | 229 |
| DISPATCHED | 60,075 | 3,001 | 229 |
| BREAK | 9,679 | 23,943 | 198 |

**Monthly distribution (zone-resolved rows):**

| month | intervals | zones active | total hours |
| --- | --- | --- | --- |
| 2024-01 | ~7,800 | 207 | ~10,400 |
| 2024-02 | ~8,000 | 214 | ~10,900 |
| 2024-03 | ~9,500 | 213 | ~13,500 |
| 2024-04 | ~9,200 | 215 | ~13,100 |
| 2024-05 | ~9,800 | 225 | ~14,200 |
| 2024-06 | ~9,300 | 220 | ~13,300 |

Dec 2023 (15 rows, 0 zones) and Jul 2024 (6 rows, 3 zones) are boundary fragments.

### Sizing verdict

**Bring the complete table.** 189,904 zone-resolved rows is small. No sampling needed. The model will filter to `zone_key IS NOT NULL` via the join to `dim_zone`, which naturally excludes LOGIN, LOGOUT, and pre-zone AVAILABLE intervals.

### Join expectations

| Join | Type | Evidence |
| --- | --- | --- |
| `fct_status_interval` → `dim_zone` on `zone_key` | Mandatory many-to-one | Existing production join in `agg_zone_occupancy_hourly` and `fct_status_interval` itself. 245 zones, each interval resolves to at most one current-version zone. |

### Boundary export shape

```sql
SELECT i.*, z.zone_natural_key, z.zone_name, z.borough_name, z.is_airport_zone
FROM core.fct_status_interval i
JOIN core.dim_zone z ON i.zone_key = z.zone_key AND z.is_current_version
WHERE i.zone_key IS NOT NULL
```

No row cap needed — the complete filtered population fits comfortably.
