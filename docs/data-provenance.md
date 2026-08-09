# Data provenance — what is real and what is not

This warehouse mixes genuine New York City TLC open data with two invented source
systems. The mixture is deliberate: the TLC feed supplies real mess and real
scale, and the invented systems supply the identity, event-stream and
aggregate-pyramid structure that TLC's trip records do not carry.

**Read this before treating any number here as a fact about New York.** Some
findings from this warehouse are genuine; others are artefacts of a generator,
and the two are not distinguishable from the tables alone.

Everything is reproducible: `tools/build_domain.py` downloads and lands the real
data, and `tools/build_mdm.py` / `tools/build_fleet_ops.py` regenerate the
invented systems deterministically from it.

---

## Tier 1 — Real, downloaded from TLC

Source: <https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page>
13 files, ~336 MB, January–June 2024. Landed verbatim; the only additions are
the ingestion columns `_load_id`, `_source_file` and `_loaded_at`.

| Table | Rows | Source file |
| --- | ---: | --- |
| `bronze.yellow_tripdata` | 20,332,093 | `yellow_tripdata_2024-01..06.parquet` |
| `bronze.green_tripdata` | 339,807 | `green_tripdata_2024-01..06.parquet` |
| `bronze.taxi_zone_lookup` | 265 | `taxi_zone_lookup.csv` |

`silver.trips` (20,671,899 rows) is **real data, transformed** — union, rename,
type, deduplicate. So is everything derived from it in `staging`, `marts/core`
and `marts/agg`.

Genuine in these tables: every timestamp, zone id, trip distance, fare, tip,
toll, surcharge, payment type, rate code and vendor id. Including the mess —
negative totals, zero-distance trips, `RatecodeID` 99, the sparse-vendor null
cluster, and the `Airport_fee` value spread — all of that is TLC's, not ours.

## Tier 2 — Real-world facts, hand-transcribed

True statements about the world, typed from the TLC data dictionary and public
rate schedules rather than downloaded from a file. They carry transcription risk
that Tier 1 does not.

| Where | What is genuine |
| --- | --- |
| `bronze.payment_type_ref`, `rate_code_ref`, `vendor_ref` | TLC code-to-label mappings |
| `mdm_raw.rate_plan_master` | Rate codes 1–6 plus the observed 99; the JFK flat fare of $70 |
| `mdm_raw.fare_regime_master` | Improvement surcharge $0.30 → $1.00; MTA tax $0.50; congestion surcharge $2.50 yellow / $2.75 green; airport access fee $1.25 → $1.75 |
| `mdm_raw.vendor_master` | Vendor ids and names — CMT, VeriFone, Curb Mobility, Myle, Helix are the real TLC technology providers, and the VeriFone-to-Curb rebrand really happened |
| `mdm_raw.calendar_master` | 2024 US federal holidays, the 8 April solar eclipse, the St Patrick's Day parade |
| `mdm_raw.borough_master` | Borough names and codes; populations and areas approximately census-accurate |
| `mdm_raw.payment_method_master.tip_is_captured` | Genuine: the meter records no cash tips, so a cash trip's zero tip is unmeasured rather than absent |

**Known softness.** The *rates* in `fare_regime_master` are real; their
**effective dates are approximate**. The VeriFone-to-Curb changeover date is
likewise approximate. Neither is safe as a citation, and any analysis that turns
on exactly when a regime changed should verify the date against TLC directly.

## Tier 3 — Real key, invented attributes

The join keys and the classifications that carry business meaning are real. The
enrichment columns around them are hash-derived and mean nothing.

| Table | Real columns | Invented columns |
| --- | --- | --- |
| `mdm_raw.zone_master` | `location_id`, `borough_name`, `zone_label`, `tlc_service_zone`, `is_airport_zone`, `zone_class` | `centroid_lat`, `centroid_lon`, `area_sq_mi`, `resident_population`, `is_congestion_zone`, `demand_tier`, and **the entire versioning** — `valid_from_date`, `valid_to_date`, `source_version` |
| `mdm_raw.zone_poi` | the three airport points of interest | the other 269 assignments |
| `mdm_raw.payment_method_master` | codes, labels, `tip_is_captured` | `settlement_class`, `settlement_days`, `processor_fee_pct`, `counts_as_revenue` |
| `mdm_raw.vendor_master` | ids, names, the rebrand | `contract_tier`, `is_approved` |
| `mdm_raw.rate_plan_master` | codes, names, flat-fare amount, airport applicability | `pricing_model`, `is_metered_baseline` |
| `mdm_raw.borough_master` | names, codes, population, area | `reporting_region`, `is_core_market` |

> **The coordinates are fake and look real.**
> `centroid_lat` / `centroid_lon` fall in a plausible NYC range but are hash
> output. JFK reads `40.6034` where the true centroid is about `40.641`, and
> `resident_population = 23,862` at an airport is nonsense. Any distance,
> density or mapping calculation built on these columns produces garbage that
> passes a smell test. The same applies to `area_sq_mi`.

Worth separating from the rest of this tier: **`tlc_service_zone` is genuine
reference data and is semantically load-bearing.** It is the column whose
`'Airports'` value silently excludes Newark, because EWR carries its own
`service_zone`. That behaviour is a real property of TLC's lookup, not an
artefact of this project.

The Type 2 versioning deserves the same care in the other direction. `dim_zone`
and `dim_vendor` exercise real SCD2 mechanics — half-open intervals, as-of
joins, the multiplication hazard — but **the version history itself is
manufactured**. Seven zones carry a second version because the generator gave
them one. No TLC re-designation is being represented.

## Tier 4 — Fully synthetic

No real counterpart. Invented wholesale.

| Table | Rows |
| --- | ---: |
| `ops_raw.garage` | 6 |
| `ops_raw.vehicle` | 420 |
| `ops_raw.driver` | 760 |
| `ops_raw.lease_agreement` | 760 |
| `ops_raw.shift` | 73,041 |
| `ops_raw.trip_assignment` | 977,754 |
| `ops_raw.driver_status_event` | 3,775,364 |
| `ops_raw.maintenance_event` | 848 |
| `mdm_raw.weather_daily` | 1,092 |

**Harbour Point Taxi Management does not exist.** Nor do its garages, medallion
numbers, VINs, drivers, hack licence numbers, lease terms or maintenance
records. TLC trip records carry no driver or vehicle identity at all, which is
precisely why this layer had to be invented.

`weather_daily` is a seasonal sine curve plus hash noise. It is **not** NOAA
data and does not correspond to the weather on those dates.

One qualification worth keeping in mind: the *identities* in `ops_raw` are
invented, but the *timing skeleton* is real. Shifts are derived from actual gaps
between real trip timestamps, `trip_assignment.trip_key` points at real trips,
and the status stream brackets real pickup and dropoff times. So shift lengths,
trip sequencing and occupancy distributions behave plausibly. Which driver drove
which medallion is fiction.

---

## What this means for analysis

**Safe to treat as real findings**

Anything about trips, zones, fares, tips, payment behaviour, airport volumes,
surcharge patterns, or data quality in the TLC feed. Concretely, all of these
are genuine properties of the source:

- `service_zone = 'Airports'` excludes Newark
- `Airport_fee` carries 1.75, −1.75, 1.25 and null in the same column
- `Airport_fee` exists only on yellow, and only in bronze
- cash trips record a tip on 0.04% of airport trips versus 94.2% on card
- zone ids 264 and 265 join the lookup cleanly and carry no real borough
- the trip-to-zone join has zero unmatched rows and no fanout across all 20.67M trips

**Not real-world claims**

Every driver, vehicle, garage and occupancy number. `mart_driver_scorecard`
ranking one driver above another says nothing about New York. Weather-to-demand
correlations are pure artefact — the weather does not match what actually fell
on those days, so any relationship found is a relationship between two
generators.

These tables earn their place by giving the warehouse a hard join graph, a
multi-million-row event stream to sessionize, and a genuine aggregate pyramid.
They are a test of the *mechanism*, not a source of insight about taxis.

**The honest summary:** every dollar in this warehouse is real; every person is
not.
