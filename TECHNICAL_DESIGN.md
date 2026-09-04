# Turnout: Technical Design

Python 3.12, Strands Agents SDK (Python), Amazon Bedrock, Amazon Bedrock AgentCore, AWS CDK. This document is complete enough to build from.

---

## 1. Architecture overview

```
                                 +------------------------------+
                                 |   Web App (Next.js, Amplify) |
                                 |   Landing, Station Board,    |
                                 |   Network View, Trace Viewer,|
                                 |   Simulated Phones, API docs |
                                 +---------------+--------------+
                                                 |
                                       HTTPS, Cognito (chief) or
                                       API key (integrators, judges)
                                                 |
                                 +---------------v--------------+
                                 |  API Gateway (REST) + Lambda |
                                 |  usage plans, API keys, WAF  |
                                 +---------------+--------------+
                                                 |
        +------------------------+---------------+----------------+-----------------------+
        |                        |                                |                       |
+-------v--------+     +---------v---------+            +---------v---------+   +---------v---------+
| AgentCore      |     | AgentCore Runtime |            | AgentCore Runtime |   | EventBridge cron  |
| Runtime:       | A2A | Riverton Agent    |    A2A     | Cedar Hollow Agent|   | hourly Watch,     |
| Millbrook Agent|<--->| (same code, own   |<---------->| (same code, own   |   | 06:30 Roll Call,  |
| (Strands Graph)|     |  config + memory) |            |  config + memory) |   | nightly Cert Clock|
+---+---+---+----+     +-------------------+            +-------------------+   +-------------------+
    |   |   |
    |   |   +-------------------------------------+
    |   |                                         |
    |   +--------------------+                    |
    |                        |                    |
+---v--------------+  +------v-----------+  +-----v-------------------+
| AgentCore Memory |  | AgentCore Gateway|  | AgentCore Code          |
| per department:  |  | MCP tools:       |  | Interpreter:            |
| volunteer        |  |  roster (DDB)    |  |  risk_engine.py         |
| response patterns|  |  calls (DDB)     |  |  coverage heatmap PNG   |
| chief prefs,     |  |  sms (EUM)       |  +-------------------------+
| ledger           |  |  weather (NWS)   |
+------------------+  |  neris (mock API)|  +-------------------------+
                      |  ledger (DDB)    |  | AgentCore Identity      |
                      +------------------+  |  outbound: SMS, NERIS   |
                                            |  inbound: A2A peer trust|
+------------------+  +------------------+  +-------------------------+
| DynamoDB tables  |  | S3: voice notes, |
| (single-table)   |  | heatmaps, NERIS  |  +-------------------------+
+------------------+  | drafts           |  | AgentCore Observability |
                      +------------------+  |  OTel -> CloudWatch     |
+------------------+                        |  trace viewer API       |
| End User         |  +------------------+  +-------------------------+
| Messaging SMS    |  | Amazon Transcribe|
| (two-way, TFN)   |  | (voice debrief)  |
+------------------+  +------------------+
```

Each department is one deployment of the same agent code with its own configuration, memory namespace, A2A endpoint, and AgentCard. Three departments are deployed for the demo.

---

## 2. Strands patterns used, and why each

| Pattern | Where | Why this pattern and not another |
|---|---|---|
| `Agent` with tools | Every agent | The base unit. Tools are typed Python functions with docstrings so the schema is explicit. |
| `GraphBuilder` graph with conditional edges and `set_max_node_executions` | The department's coverage loop: Watch to Closer to Neighbor to Chief Gate, with a bounded retry back to Closer | The flow is deterministic and auditable. A chief must be able to see exactly why a decision was reached. Swarm would let agents hand off freely, which is wrong for a safety workflow. |
| Agents as tools | Scribe and Cert Clock are invoked as tools by the department orchestrator | They are self-contained jobs with clear inputs and outputs. |
| A2A server (`strands.multiagent.a2a.server`) | Each department exposes `request_coverage`, `confirm_coverage`, `cancel_coverage`, `ledger_summary` | Departments are separate organizations. A2A is the protocol built for agents across organizational boundaries, with AgentCard discovery. |
| A2A client as a tool inside the Graph | Neighbor agent calls peers | Strands supports remote A2A agents as tools and as Graph nodes in Python. |
| Hooks | Every agent | A `BeforeToolInvocation` hook enforces the volunteer contact policy (quiet hours, weekly ask limit). An `AfterModelInvocation` hook writes structured decision logs. This is how we prove the policy is enforced in code, not in a prompt. |
| Session management with AgentCore Memory | Every agent | Long-lived per-department context: who usually says yes, chief preferences, ledger. |
| Structured output | Roll Call parsing, Chief Gate message, NERIS draft | Pydantic models so downstream code never parses prose. |

---

## 3. The agents

All agents share a system prompt preamble: the department's identity, the current time in the department's time zone, the safety rules (never page, never commit without approval), and the output contract.

### 3.1 Roll Call

- Trigger: EventBridge at 06:30 local, and on any inbound SMS.
- Tools: `get_roster`, `send_sms`, `record_availability`, `get_pending_polls`.
- Behavior: sends the daily poll to each active member for the next day's high-risk windows only (not the whole week, to keep it to one text). Parses replies with structured output into `{member_id, window, status: available|unavailable|partial, note}`. Handles "Y", "N", "till 2", "not this week", "STOP". On "STOP", sets opt-out and confirms.
- Eval set: 200 synthetic replies with labels. Target 97 percent.

### 3.2 Watch

- Trigger: EventBridge hourly, and after any availability change.
- Tools: `get_availability(window_range)`, `get_call_history(days=365)`, `get_weather_alerts(zone)`, `risk_engine` (Code Interpreter), `store_gaps`.
- Behavior: builds the 7-day hourly coverage matrix per district, computes qualified-crew feasibility (see 4.2), calls the risk engine for every window that is under minimum crew, stores gaps with risk level and explanation, and emits the ordered list of gaps to the Graph.
- Output: `GapList` with fields `window_start, window_end, district, missing_roles, expected_calls, p_understaffed, hazard_multiplier, risk_score, level, explanation`.

### 3.3 Closer

- Trigger: Graph edge from Watch when any gap has level high or critical.
- Tools: `get_member_response_stats` (from Memory), `send_sms`, `propose_swap`, `record_availability`.
- Behavior: for each gap, ranks members not yet available by predicted yes probability for that window, filtered by required role. Sends at most two targeted asks per gap, spaced by 20 minutes, honoring quiet hours and the weekly limit (enforced by the hook, not the prompt). If two members' availabilities can be swapped to close the gap without opening another, proposes the swap to both. Waits up to the configured window (default 90 minutes) for replies. Marks the gap closed or unresolved.
- Ask copy is fixed by template so members get a consistent, short message: "Millbrook VFC: Thu 10a to 2p needs a driver. You usually can. Reply Y or N."

### 3.4 Neighbor

- Trigger: Graph edge from Closer when a critical or high gap is unresolved.
- Tools: `discover_peers` (reads AgentCards from configured peer URLs), `a2a_request_coverage`, `evaluate_offers` (Code Interpreter), `get_ledger`.
- Behavior: sends a structured `CoverageRequest` to each peer within the mutual aid agreement. Each peer's agent replies with `CoverageOffer {can_cover: bool, estimated_delay_min, roles, conditions, ledger_delta}` or a decline with reason. Neighbor scores offers: lower delay is better, ledger balance closer to zero is better, and a peer that is itself in a high-risk window is penalized. Produces the best offer and one alternative.
- Never confirms. Confirmation is the chief's decision.

### 3.5 Chief Gate

- Trigger: Graph edge from Neighbor with an offer, or from Closer when a gap is unresolved and no peer can help.
- Tools: `send_sms(chief)`, `await_reply`, `a2a_confirm_coverage`, `update_ledger`, `store_decision`.
- Behavior: composes a single message under 300 characters with the window, the risk level and its one-line explanation, the recommended action, and the reply options. Example: "Thu 10a to 2p: CRITICAL (1 to 2 calls expected, 0 drivers, ice storm warning). Riverton can cover, 9 min delay. Reply 1 to approve, 2 for options, 3 to leave open." On approval, confirms with the peer over A2A, updates both ledgers, and notifies the members involved. On "options", sends the alternative. On "leave open", records the decision and re-checks in 3 hours.
- If the chief does not reply within 2 hours and the gap starts within 24 hours, escalates to the deputy chief.

### 3.6 Scribe

- Trigger: an inbound voice note (MMS or app upload) or the chief typing "debrief".
- Tools: `transcribe_audio` (Amazon Transcribe), `get_incident_context` (dispatch time, units, responders from the roster), `draft_neris_report` (structured output against the NERIS schema subset), `store_draft`, `send_sms(chief)`.
- Behavior: transcribes, extracts the NERIS-required fields we support (incident type up to three categories, location, units, personnel count, actions taken, casualties, times), fills known values from context, marks uncertain fields, and sends the chief a link to review. Submission is a button on the Station Board, never automatic.
- NERIS: the real system requires department credentials. The demo uses a mock endpoint with the public NERIS data schema. The design includes an AgentCore Browser task to fill the real portal as a documented extension.

### 3.7 Cert Clock

- Trigger: EventBridge nightly.
- Tools: `get_certifications`, `get_training_calendar`, `send_sms`, `create_training_event`.
- Behavior: finds certifications expiring within 90 days, checks whether a qualifying course is already scheduled, proposes a date to the member, and puts it on the calendar. 30 days out, escalates to the chief with a one-line summary. Marks members as non-response-eligible on the day a required cert lapses, and tells the Watch agent so coverage math is correct.

---

## 4. Deterministic logic

### 4.1 Why deterministic

A judge who reads "the agent considers weather and call patterns" learns nothing. A judge who reads a trace showing `expected_calls=1.4, p_understaffed=0.71, hazard=1.8, risk=0.83` learns that the system is real. All risk math runs as Python inside AgentCore Code Interpreter, called as a tool, with inputs and outputs logged.

### 4.2 Qualified crew feasibility

Configuration per department:

```
min_crew:
  fire:  { driver_operator: 1, firefighter: 2 }
  ems:   { emt: 1, driver: 1 }
```

For a window, the set of available members and their roles is known. Feasibility is whether the requirement can be satisfied by assigning each member at most one role. This is a small bipartite matching, solved exactly. If infeasible, the missing roles are reported.

### 4.3 Risk engine

Inputs: window, district, available members with per-member response probability, 12 months of call history, active weather alerts.

```
lambda_window   = base_rate(hour_of_day, day_of_week) * month_factor(month) * duration_hours
                  where base_rate is estimated from the department's own call history
                  with additive smoothing toward the NFPA national profile

p_i             = posterior mean response probability for member i in this type of window
                  Beta(alpha0 + yes_i, beta0 + no_i), prior mean 0.32 from the
                  17 to 47 percent range in the volunteer dispatch literature

p_understaffed  = probability that the set of members who actually respond
                  cannot satisfy min_crew; computed exactly by enumerating
                  response subsets when n <= 12, otherwise by Monte Carlo (10,000 draws)

hazard          = product of active alert multipliers
                  ice_storm_warning 1.8, winter_storm_warning 1.6, heat_advisory 1.4,
                  excessive_heat_warning 1.6, red_flag_warning 2.0, high_wind_warning 1.3,
                  flood_warning 1.5, none 1.0

severity        = weighted share of time-critical call types in this window's history
                  (cardiac, respiratory, structure fire, MVC with entrapment) in [0.5, 1.0]

risk_score      = 1 - exp(-(lambda_window * hazard) * p_understaffed * severity)

level           = critical if risk_score >= 0.75
                  high     if >= 0.50
                  elevated if >= 0.25
                  low      otherwise

explanation     = f"{lambda_window*hazard:.1f} calls expected, {missing_roles}, "
                  f"{int(p_understaffed*100)}% chance nobody qualified responds"
                  + (f", {alert_name}" if hazard > 1 else "")
```

Every number is returned to the agent and stored on the gap record. The Station Board shows the formula on hover of any risk badge.

Tests: fixed inputs with hand-computed expected outputs; monotonicity tests (more available members never increases risk; a hazard never decreases risk); boundary tests at each level threshold.

### 4.4 Offer evaluation

```
score(offer) = w_delay * clamp(1 - delay_min / 30, 0, 1)
             + w_ledger * clamp(1 - abs(ledger_balance_hours_after) / 20, 0, 1)
             + w_peer_risk * (1 - peer_current_risk)
weights: 0.5, 0.3, 0.2
```

Offers with delay above the department's configured maximum (default 20 minutes) are shown but flagged.

---

## 5. A2A protocol design

### 5.1 AgentCard

Each department serves `/.well-known/agent.json`:

```json
{
  "name": "Riverton Fire and Rescue Coverage Agent",
  "description": "Negotiates mutual aid coverage windows with neighboring departments.",
  "url": "https://riverton.turnout.example/a2a",
  "version": "1.0.0",
  "capabilities": { "streaming": false, "pushNotifications": false },
  "skills": [
    { "id": "request_coverage", "name": "Request coverage", "description": "Ask this department to cover a time window and district." },
    { "id": "confirm_coverage", "name": "Confirm coverage", "description": "Confirm a previously offered coverage window." },
    { "id": "cancel_coverage", "name": "Cancel coverage", "description": "Cancel a confirmed window with a reason." },
    { "id": "ledger_summary", "name": "Ledger summary", "description": "Return the mutual aid balance between the two departments." }
  ],
  "authentication": { "schemes": ["bearer"] }
}
```

### 5.2 Messages

All A2A task payloads are JSON with Pydantic models on both sides.

```
CoverageRequest  { request_id, from_dept, window_start, window_end, district,
                   roles_needed, risk_level, risk_explanation, expires_at }
CoverageOffer    { request_id, can_cover, estimated_delay_min, roles, conditions,
                   ledger_delta_hours, valid_until, reason_if_declined }
CoverageConfirm  { request_id, confirmed_by, confirmed_at }
CoverageCancel   { request_id, cancelled_by, reason }
LedgerSummary    { peer, hours_given, hours_received, balance_hours }
```

### 5.3 Trust

- Each pair of departments in a mutual aid agreement exchanges a bearer credential provisioned through AgentCore Identity. Requests from unknown peers are rejected.
- A peer can only request coverage, never read the roster.
- The receiving agent evaluates the request against its own coverage and risk before offering, and its own chief must approve any confirm unless auto-approval is configured.

### 5.4 Demo topology

Millbrook, Riverton, and Cedar Hollow are mutual peers. Millbrook is the department the video follows. Riverton is well-staffed on the demo day. Cedar Hollow is itself at high risk in the same window and declines with that reason, which shows the network protecting the weaker neighbor.

---

## 6. AgentCore mapping, with the reason for each

| Service | Use | Why it is the right primitive here |
|---|---|---|
| Runtime | One runtime per department running the Strands Graph and the A2A server | Long-lived sessions (the coverage loop can wait 90 minutes for replies), isolation per organization, scales to zero between runs |
| Memory | Per-department namespace: member response history summaries, chief preferences ("prefers Riverton over Cedar Hollow for the north district"), ledger context | The agent must get better at predicting who says yes; this is exactly persistent, retrievable context |
| Gateway | Wraps DynamoDB access, End User Messaging SMS, the NWS API, the mock NERIS API, and the ledger as MCP tools | One tool interface across agents; credentials never live in agent code; tools are discoverable |
| Identity | Outbound: SMS and NERIS credentials on behalf of the department. Inbound: peer bearer credentials for A2A | Agents acting on behalf of an organization with scoped, auditable credentials is the Identity use case |
| Code Interpreter | Risk engine, feasibility matching, offer scoring, coverage heatmap rendering | Deterministic math must run as code with logged inputs and outputs, not as model reasoning |
| Browser | Documented extension: fill the NERIS web portal | The real NERIS may not expose an API to a small department; a managed browser is the honest path |
| Observability | OpenTelemetry traces for every Graph run and every A2A exchange, surfaced in the web Trace Viewer | The judge can watch the negotiation happen |

---

## 7. Data model

DynamoDB single-table design, `Turnout`, partition key `pk`, sort key `sk`, with a GSI on `gsi1pk/gsi1sk` for time-range queries.

| Entity | pk | sk | Key attributes |
|---|---|---|---|
| Department | `DEPT#<id>` | `META` | name, tz, districts[], min_crew, peers[], quiet_hours_default, weekly_ask_limit, auto_approve_rules, chief_phone, deputy_phone |
| Member | `DEPT#<id>` | `MEMBER#<id>` | name, phone, roles[], certs[{type, expires}], quiet_hours, opted_out, asks_this_week |
| Availability | `DEPT#<id>` | `AVAIL#<window_start>#<member_id>` | status, source (poll, ask, swap), note, recorded_at |
| Call | `DEPT#<id>` | `CALL#<timestamp>` | type, district, duration_min, responders[], time_critical |
| Gap | `DEPT#<id>` | `GAP#<window_start>#<district>` | missing_roles, expected_calls, p_understaffed, hazard, severity, risk_score, level, explanation, status, resolution |
| Decision | `DEPT#<id>` | `DECISION#<timestamp>` | gap_ref, message_sent, reply, action_taken, trace_id |
| LedgerEntry | `DEPT#<id>` | `LEDGER#<peer>#<timestamp>` | direction (given, received), hours, request_id |
| Incident | `DEPT#<id>` | `INCIDENT#<id>` | audio_s3, transcript, neris_draft (json), status, submitted_at |
| Message | `DEPT#<id>` | `MSG#<timestamp>#<member_id>` | direction, body, purpose (poll, ask, decision, cert) |

S3 bucket `turnout-artifacts`: voice notes, heatmap PNGs, NERIS drafts. Lifecycle: 90 days.

---

## 8. Public API

Base URL: `https://api.turnout.example/v1`. Auth: `x-api-key` header via API Gateway usage plans. A sandbox key is printed on the developer page and scoped to the demo departments.

| Method | Path | Purpose |
|---|---|---|
| POST | `/departments` | Create a department with config |
| POST | `/departments/{id}/members` | Add or update members |
| POST | `/departments/{id}/availability` | Push availability (for CAD or scheduling integrations) |
| GET | `/departments/{id}/coverage?from=&to=` | Hourly coverage and gaps with risk |
| GET | `/departments/{id}/gaps` | Open gaps |
| POST | `/departments/{id}/gaps/{gapId}/decision` | Approve, decline, or request options |
| POST | `/departments/{id}/incidents/debrief` | Upload audio or text; returns NERIS draft |
| GET | `/departments/{id}/ledger` | Mutual aid balances |
| POST | `/departments/{id}/simulate/inbound-sms` | Sandbox only: simulate a member reply |
| GET | `/departments/{id}/traces/{traceId}` | Trace summary for the web viewer |
| GET | `/.well-known/agent.json` (per department host) | A2A AgentCard |
| POST | `/a2a` (per department host) | A2A JSON-RPC endpoint |

OpenAPI 3.1 spec is generated from the Lambda handlers and published at `/openapi.json` and rendered on the developer page. Rate limits: sandbox 60 requests per minute; the error body explains how to request a higher tier.

---

## 9. Web application

Next.js 15, App Router, TypeScript, Tailwind, shadcn/ui, deployed on AWS Amplify Hosting. Auth for chiefs via Amazon Cognito. "Judge mode" is an unauthenticated route that loads the demo department with a read-mostly session and a reset button.

Pages:

| Route | Purpose |
|---|---|
| `/` | Landing page (see `LANDING_PAGE.md`) |
| `/demo` | Judge mode entry: picks Millbrook, loads the demo scenario, offers "Play the week" |
| `/board` | Station Board: 7-day coverage heatmap by district, gap list with risk badges (formula on hover), pending decisions, recent incidents, cert warnings |
| `/network` | Network View: map with the three departments, live A2A messages animating along edges, ledger balances |
| `/phones` | Simulated phones: chief's phone and any member's phone side by side, showing the real SMS content, with reply buttons |
| `/traces` | Trace Viewer: the latest Graph run as a timeline with tool inputs and outputs, A2A calls, memory reads; link to the CloudWatch trace |
| `/incidents/{id}` | NERIS draft review and submit |
| `/developers` | API quickstart, sandbox key, OpenAPI |
| `/judges` | The five criteria, each with links to evidence |
| `/references` | Every citation |

Real-time updates: the board and network pages subscribe to a WebSocket (API Gateway WebSocket) fed by DynamoDB Streams, so an A2A exchange appears within a second.

---

## 10. Infrastructure and deployment

- AWS CDK (Python) app with stacks: `Data` (DynamoDB, S3), `Agents` (three AgentCore runtimes, Memory, Gateway, Identity, Code Interpreter config), `Api` (API Gateway, Lambdas, usage plans, WAF), `Messaging` (End User Messaging phone number, SNS inbound topic, Lambda router), `Web` (Amplify app), `Ops` (EventBridge schedules, health check, alarms, status page).
- Bedrock model access enabled in us-east-1 and us-west-2.
- Secrets in AWS Secrets Manager; none in the repo. `.env.example` documents every variable.
- Health check Lambda every 5 minutes: calls `/departments/millbrook/coverage`, verifies a 200 and a fresh timestamp, posts status to a small public status page and to the team's phone on failure.
- Cost controls: budgets alarm at 30 and 45 dollars; model calls capped per hour per department.

---

## 11. Testing and evaluation

| Layer | Method |
|---|---|
| Risk engine, feasibility, offer scoring | pytest with hand-computed fixtures, monotonicity and boundary tests |
| Roll Call parsing | 200 labeled synthetic replies; report accuracy and confusion matrix in README |
| Closer policy | Hook-level tests proving quiet hours and weekly limits block sends |
| A2A | Contract tests against the Pydantic models; an integration test that runs two local A2A servers and completes a request, offer, confirm cycle |
| Scribe | 20 synthetic voice debriefs with expected NERIS fields; report field accuracy |
| Graph | Scenario tests: "gap closed by Closer," "gap closed by Neighbor," "chief declines," "peer declines because at risk" |
| Web | Playwright smoke tests in light and dark, 360 px and 1280 px; axe-core accessibility |
| Load | 50 concurrent judge sessions on the sandbox API |

Results tables are generated by CI and committed to `docs/EVAL.md`, which the README links.

---

## 12. Repository layout

```
turnout/
  README.md
  LICENSE                      (MIT)
  docs/
    architecture.png, architecture-dark.png, architecture.drawio
    EVAL.md, LATER.md, SAFETY.md, NERIS_SCHEMA.md
  agents/
    department/                 the Strands Graph and agents
      graph.py, roll_call.py, watch.py, closer.py, neighbor.py, chief_gate.py, scribe.py, cert_clock.py
      hooks.py, prompts/, models.py (Pydantic)
    a2a/
      server.py, client.py, cards/
    tools/
      roster.py, calls.py, sms.py, weather.py, neris.py, ledger.py
    code_interpreter/
      risk_engine.py, feasibility.py, offers.py, heatmap.py
  infra/                        CDK app and stacks
  api/                          Lambda handlers, OpenAPI generation
  web/                          Next.js app
  data/
    generate.py                 synthetic departments, members, 12 months of calls
    scenarios/demo_week.json
  tests/
  evals/
  .github/workflows/ci.yml
```

---

## 13. Sequence: the demo gap, end to end

1. 06:30 Roll Call texts 14 Millbrook members about Thursday's daytime windows. Nine reply within an hour.
2. 07:30 Watch runs. Thursday 10:00 to 14:00, north district: one firefighter available, no driver. NWS has an ice storm warning for Thursday. Risk engine: 1.4 expected calls, 71 percent chance no qualified crew responds, hazard 1.8, severity 0.8. Score 0.83, critical.
3. 07:31 Closer asks the two members with the highest predicted yes for that window. One is at quiet hours until 08:00; the hook defers the send. Both decline by 08:40.
4. 08:41 Neighbor discovers Riverton and Cedar Hollow AgentCards, sends CoverageRequest to both. Riverton offers, 9-minute delay, ledger delta +4 hours. Cedar Hollow declines: "own north district at high risk in that window."
5. 08:42 Chief Gate texts the chief one message. Chief replies 1.
6. 08:44 A2A confirm to Riverton. Both ledgers updated. Riverton's chief had auto-approval for delays under 10 minutes; their agent confirms without interrupting them. Millbrook members are told coverage is arranged.
7. Thursday 11:52 a call comes in. Riverton responds. Afterward the Riverton officer leaves a voice note. Scribe drafts the NERIS report, marks two fields uncertain, and both chiefs see it.
8. The Trace Viewer shows every step with inputs and outputs. Total chief time: eight seconds.
