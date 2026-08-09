# Candidate intents

Six business requests to run through intent capture against this warehouse.

Each is written the way it actually arrived — a message from someone who knows
their business and not the warehouse. They are **deliberately underspecified**.
None names a table, a column, a grain or a metric definition, because working
that out is the job, and a request that hands over its own answer tests nothing.

These carry no technical framing on purpose. There is no scenario label, no hint
about which are builds and which are fixes, and no indication of what any of
them will turn out to involve. Classification is the first thing the session
does, not something this file has already done for it.

Between them they span new source onboarding, new models over existing data,
changes to something already shipped, reconciliation work, open-ended analysis
with no artifact at the end, and a compliance deadline.

## Running one

Start a session with nothing but the repository and one intent file. Let it read
`CONTEXT.md`, `docs/adr/` and `docs/data-provenance.md` for itself, and work
from there.

Give it one intent at a time. Reading all six at once tells it more about the
shape of the exercise than any real backlog would.

Expect to be asked questions. Answer as the requester would — from the business,
not from the schema. If a question can only be answered by reading the
warehouse, that is a sign it should have been read rather than asked.

| # | From | Subject |
| --- | --- | --- |
| 01 | Commercial | Losing airport work to the apps |
| 02 | Commercial / Finance | Concession renegotiation at LGA and JFK |
| 03 | Fleet Operations | Night crew say the scorecard is rigged |
| 04 | Finance Reporting | Two numbers in the Monday pack disagree |
| 05 | Commercial | Lease repricing — what do drivers actually earn |
| 06 | Compliance | Wheelchair-accessible service audit |
