# Evaluation results

Generated 2026-09-04 14:50 UTC.

## Reply parsing

Members answer a poll however they like. The rule parser handles the common cases without a model
call, so a member's reply is acknowledged in seconds rather than after a round trip. The model is
asked only when this returns `unknown`.

**82 phrasings, 100.0% read correctly.**

| Intent | Phrasings covered |
|---|---|
| yes | Y, yes, yep, yeah, yup, sure, ok, can do, in, i can, count me in, 10-4, roger, affirmative, available |
| no | N, no, nope, nah, can't, cannot, out, not available, negative, busy, working, not this week, out of town, on vacation, and free text such as "sorry, can't, at the plant all day" |
| partial | till 2, until 2pm, til noon, before 11, morning only, afternoon, after 1, from 3pm, and the same inside a longer sentence |
| stop, start, help, limits, status, gaps | the keyword forms, case insensitive |
| decision | 1, 2, 3, 2a, 2b, UNDO |
| unknown | anything it cannot read, which is escalated to the model rather than guessed |

A bare number under 7 in a partial window is read as the afternoon, because "till 2" in a daytime
coverage question never means two in the morning.

## Risk engine and crew feasibility

Exact and deterministic, so they are unit tested rather than evaluated. `pytest -q` runs 91 tests.

| Property | How it is checked |
|---|---|
| Hand-computed probability | One driver at 0.5 and two firefighters at 1.0 must give exactly 0.5 |
| Monotonic in members | Adding an available member never raises the risk score |
| Monotonic in hazard | A weather alert never lowers the risk score |
| Level boundaries | Each of the four thresholds is asserted |
| Crew matching | One person who is both driver and firefighter cannot fill two slots |
| Thin history | Under 90 days, the explanation says the estimate leans on a national pattern |

## Message length

Every template is rendered and length-checked in the test suite: member messages stay under 160
characters so they never split, chief decision messages under 300.

## Agent-to-Agent

Five tests run real A2A over HTTP between separate department servers, including one that asks a
peer for its roster and asserts that no roster comes back.
