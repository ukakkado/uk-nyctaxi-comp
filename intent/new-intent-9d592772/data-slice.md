# Data Slice: Zone by Month Utilisation

One section per transformation deliverable in `intent.md`.

---

## Deliverable 1: `agg_zone_utilisation_monthly`

### Candidate input

`core.fct_status_interval` joined to `core.dim_zone` (current version, `is_current_version = true`).

`fct_status_interval` is already at the interval grain with `zone_key`, `status_code`, and `interval_seconds` — exactly the columns the model needs. No pre-aggregated table sits at zone × month; `agg_zone_occupancy_hourly` is hourly and would require re-aggregation with potential precision loss on the hour boundaries. Going directly from the interval fact is simpler and more accurate.

`dim_zone` is joined for `is_unresolved_zone` (filter) and zone attributes (pass-through). The join is mandatory many-to-one (many intervals → one zone version), already proven in production by `agg_zone_occupancy_hourly`.

### Profiling evidence

| Metric | Value |
| --- | --- |
| Total rows in `fct_status_interval` | 337,069 |
| Distinct zones with data | 245 |
| Distinct months | 8 (2024-01 through 2024-07, plus 2023-12 partial) |
| Date range | 2023-12-31 to 2024-07-01 |
| Distinct status codes | 6: AVAILABLE (109K), ON_TRIP (60K), DISPATCHED (60K), LOGIN (49K), LOGOUT (49K), BREAK (10K) |
| `interval_seconds` range | 0 to 17,760 (mean 806) |
| Unresolved zones in dim | 2 (excluded per A-06) |
| Expected output rows (zone × month) | 1,305 |

### Sizing verdict

**Bring the complete table.** 337K rows is small for DuckDB-local; no sampling needed. The output is 1,305 rows — trivially materialisable.

### Strata

No stratification required. The data is small enough that every zone, month, and status code is fully represented. Boundary values of note:
- `interval_seconds = 0` exists (LOGOUT intervals) — handled by SUM naturally
- 2 unresolved zones exist and are filtered per A-06

### Join expectations

| Join | Type | Evidence |
| --- | --- | --- |
| `fct_status_interval` → `dim_zone` on `zone_key` | Mandatory many-to-one | Same join in `agg_zone_occupancy_hourly`; `dim_zone` carries `is_current_version` for version resolution |

### Bounded export shape

```sql
SELECT
    si.zone_key,
    date_trunc('month', si.interval_date) AS month_start_date,
    si.status_code,
    si.interval_seconds,
    z.zone_natural_key,
    z.zone_name,
    z.borough_name,
    z.is_unresolved_zone
FROM core.fct_status_interval si
JOIN core.dim_zone z ON si.zone_key = z.zone_key AND z.is_current_version = true
WHERE z.is_unresolved_zone = false
```

This exports all columns the model needs for grain, filtering, and metric computation. No row cap — the complete filtered set is ~335K rows after excluding the 2 unresolved zones.
