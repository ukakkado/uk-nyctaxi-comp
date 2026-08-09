# Candidate intents

Two sets of requests to run through intent capture against this warehouse.

## What these are

Each request is complete in the way a real one is: it says who is asking, what
decision it feeds, which period matters, which existing objects are involved,
and when it is due. Where an existing model is referenced it is named, so no
effort goes into working out which table someone meant.

What they do **not** do is settle the questions that decide whether the result
is any good — the grain, the measure definitions, the cohort, and what happens
at the edges. Several state openly that the requester does not know how to
settle something and would like to be told. That is the material grilling works
on.

They also carry no technical framing. There is no scenario label, no hint about
which are builds and which are fixes, and no indication of what any of them will
turn out to involve. Classification is the first thing a session does, not
something this file has already decided.

## The two sets

**Numbered intents (01–06)** arrive as emails describing a business problem.
The deliverable is open — part of the work is establishing what should be built,
or whether anything should be built at all.

**Direct requests (R1–R14)** arrive already naming the artifact: a table, an
aggregate, a column. They sound finished, and that is the trap — a request that
names its own deliverable invites building instead of asking what a row means.

| # | From | Subject |
| --- | --- | --- |
| 01 | Commercial | Losing airport work to the apps |
| 02 | Commercial / Finance | Concession renegotiation at LGA and JFK |
| 03 | Fleet Operations | Night crew say the scorecard is rigged |
| 04 | Finance Reporting | Two revenue tables disagree |
| 05 | Commercial | Lease repricing — what drivers actually earn |
| 06 | Compliance | Wheelchair-accessible service audit |

See [direct-requests.md](direct-requests.md) for the second set.

## Running one

Start a session with the repository and one request. Let it read `CONTEXT.md`,
`docs/adr/` and `docs/data-provenance.md` for itself.

**Give one at a time.** Reading several together reveals more about the shape of
the exercise than any real backlog would.

Expect to be asked questions, and answer as the requester would — from the
business, not from the schema. If a question could only be settled by reading
the warehouse, that is a sign it should have been read rather than asked.

Not every request should end in a build. One of the direct requests asks for
something the warehouse already answers, and at least one asks for data that is
not present at all. Saying so is the correct outcome, not a failure.
