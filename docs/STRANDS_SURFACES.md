# Every Strands surface, and what Turnout does with it

The judging criterion is "how thoroughly and skillfully does the project use Strands Agents". That
invites a certain kind of dishonesty, where you reach for every module in the SDK so the list looks
long. This is the list, including the parts deliberately left alone and why, because a feature used
without a reason is worse evidence of understanding than a feature rejected with one.

Strands Agents SDK 1.18.0. Every row was checked against the installed package, not the docs.

| Surface | Used | Where, or why not |
|---|---|---|
| `strands.Agent` | yes | Roll Call, Chief Gate and the peer service |
| `strands.tool` | yes | Every tool in `tools/`, typed and docstring-described |
| `strands.models.BedrockModel` | yes | Sonnet 4.6 for reasoning, Haiku 4.5 for reply parsing |
| `strands.multiagent.GraphBuilder` | yes | `agents/department.py`, conditional edges on coverage state |
| `strands.multiagent.graph.GraphState` | yes | Edge conditions read it to decide whether the chief is needed |
| `strands.hooks` | yes | `agents/hooks.py`, contact policy enforced in code not in the prompt |
| `strands.telemetry` | yes | `observability.py`, OTLP spans for AgentCore Observability |
| A2A, via `strands.multiagent.a2a` | yes | `a2a/`, a real cross-department boundary |
| `strands.session` | no | See below |
| `strands.interrupt` | no | See below |
| `strands.tools.mcp` | no | See below |
| `strands.experimental` | no | Explicitly unstable. Not in something a chief's staffing depends on |

## Hooks, and why policy is not in the prompt

`ContactPolicyHook` cancels the tool call rather than asking the model not to make it. A member who
replied STOP is never texted, and a targeted ask stops at the weekly limit, because
`BeforeToolCallEvent` sets `cancel_tool` before the send happens. The prompt says so as well. The
hook is what makes it true.

This is the distinction the whole project rests on. A volunteer who gets texted after opting out is
not a bad answer from a model, it is a promise broken, and a promise you can only keep when the
model cooperates is not a promise.

## Telemetry, and the claim it had to back

`TraceHook` emits an event for every tool call, which is what the Trace Viewer renders. Until today
the docstring on that file also claimed AgentCore Observability showed the same story, and that was
not true: no OpenTelemetry was configured anywhere in the repository. The claim is now backed by
`observability.py` rather than deleted.

Strands instruments itself with OpenTelemetry, so every agent invocation, model call and tool call
becomes a span with timings and token counts, including the path taken through the graph, which is
the part the hand-rolled events describe worst. AgentCore Observability and CloudWatch both ingest
OTLP directly.

It is off unless an endpoint is configured, and that is a decision rather than an oversight. The
submitted demo runs with no collector reachable. If tracing were on by default, every start would
spend its timeout failing to reach one. `/api/health` reports which state it is in, so the status
page cannot claim tracing that is not running.

```
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318   send spans to a collector
TURNOUT_TRACE_CONSOLE=1                             print spans, no collector needed
```

## The three that were rejected, and the reason for each

**`strands.tools.mcp`.** Turnout already has a cross-organisation boundary, and it is A2A, which is
the right protocol for it. MCP is how an agent reaches tools. A2A is how an agent reaches another
agent that has its own roster, its own chief and its own reasons to say no. Millbrook does not want
a tool call against Riverton's roster. It wants to ask Riverton's agent a question and be told no
sometimes. Adding an MCP server here would be a second protocol doing worse what the first one
already does well.

The companion project, Tally, has the opposite shape and does use MCP, for the same reason in
reverse: a sponsoring organisation reviewing a claim needs the rulebook, not a negotiation.

**`strands.session`.** Session managers persist conversation state so an agent can resume a thread
after a restart. Turnout has no threads. Roll Call runs as a scheduled sweep, and a reply arriving
by SMS webhook hours later is applied to a gap in the store, not to a conversation. What has to
survive a restart is the gap, the ledger and the message log, and those are in the store where they
can be queried, audited and shown on a board. A session transcript would be storage nobody reads.

**`strands.interrupt`.** This is the one that looks like it should fit, since the hackathon theme is
an agent that surfaces only when there is a real decision, and the chief interrupt budget in
`tools/chief.py` is exactly that. It does not fit, and the reason is worth stating.

`Interrupt` pauses an in-process agent run and resumes it with a response. Turnout escalates to a
chief by text message, and the chief may be asleep, on a call or driving. The run ends, the decision
is recorded as pending, and the reply is applied whenever it arrives, possibly hours later, possibly
never. Holding an agent run open across that would be strictly worse.

The escalation being asynchronous is the design, not a limitation of it. Using `Interrupt` here
would have added an SDK import and removed a property the product depends on.
