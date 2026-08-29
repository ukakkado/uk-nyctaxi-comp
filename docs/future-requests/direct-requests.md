# Direct requests

A second set, unlike the numbered intents. Those arrive as emails describing a
business problem and leave the deliverable entirely open. These arrive already
knowing what they want built — a table, an aggregate, a column — and they name
the objects they mean.

What they leave open is the part that decides whether the result is any good:
the grain, the filters, the measure definitions, and what happens at the edges.
That is the harder shape to grill. An open business problem invites questions. A
request that names its own deliverable sounds finished, and the temptation is to
start building instead of asking what a row is supposed to mean.

Models are named explicitly so no effort goes into working out which object was
meant. The work is in what the new one should contain.

None of them state a grain. None define their measures. Several are more
expensive than they look, one asks for something the warehouse already answers,
and at least one asks for data that is not present at all — noticing that is the
correct outcome, not a failure.

**Give one at a time.** Answer follow-ups as the requester would, from the
business. Anything settleable by reading the warehouse should be read rather
than asked.

---

**R1.** Build a vehicle scorecard — same idea as `ops.mart_driver_scorecard`,
but per medallion and month by month. The depot managers want to compare
vehicles the way they compare drivers.

**R2.** New aggregate please: pickup borough by day of week by daypart, with
trip counts, revenue and average fare. It's for roster planning.

**R3.** Add the airport surcharge as a column on `finance.mart_daily_zone_revenue`.

**R4.** Onboard the TLC high-volume for-hire feed as a new source — staging
model plus a daily zone-level aggregate, so we can put their volume next to
ours.

**R5.** `finance.mart_monthly_service_summary` needs splitting by rate plan as
well as payment method.

**R6.** New fact table at trip grain for airport pickups only, carrying the fee
components. Commercial want to query it directly rather than asking us.

**R7.** Build a driver-by-week aggregate. We have `agg.agg_driver_daily` and
`agg.agg_driver_monthly`; the shift-bidding cycle is weekly and we keep
deriving it by hand.

**R8.** Borough-level origin-destination matrix, monthly. `agg.agg_od_flow_matrix`
is far too granular for the board pack.

**R9.** Add a weather dimension onto `core.fct_trip` so we can slice demand by
conditions.

**R10.** New table: zone by month utilisation — how much of the time our cars sit
in a zone versus actually earning there.

**R11.** Extend the reporting window back through 2023 on the finance marts.
Year-on-year is the first thing the board asks for.

**R12.** Retire `finance.mart_daily_zone_revenue` and replace it with the same
thing at zone-by-daypart grain. Nobody looks at the daily number on its own.

**R13.** Add a lease-cost column to `agg.agg_driver_monthly` so we can see margin
per driver, not just revenue.

**R14.** We need a garage-level daily table. `agg.agg_garage_monthly` is too slow
for the depot managers to react to.
