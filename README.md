# Turnout

Track: Good Neighbor Agents. Target: Grand Prize.

In the fire service, the "second due" is the neighboring company that comes when yours cannot. Turnout is an agent network that makes sure there always is one.

Every other tool tells the chief who is coming. Turnout makes sure someone is.

## Documents in this folder

| File | What it covers |
|---|---|
| `PLAN.md` | Problem, audience, evidence, scope, feature list, success criteria, positioning against existing tools |
| `TECHNICAL_DESIGN.md` | Architecture, every agent, Strands patterns used, AgentCore mapping, risk engine, A2A protocol, data model, API, security, testing, deployment |
| `LANDING_PAGE.md` | Section-by-section landing page specification with final copy, InfoTip text, and references |
| `DEMO_AND_VIDEO.md` | Synthetic dataset, demo scenario, judge walkthrough, the timed video script |

Shared standards live one level up in `../STRATEGY.md` and `../DESIGN_SYSTEM.md`.

## One-paragraph summary

Volunteer fire and EMS departments protect most of rural America, and they are collapsing: volunteer numbers are at a 35-year low while calls have more than tripled, and 4.5 million Americans now live more than 25 minutes from an ambulance. The daily failure is not "no volunteers" but "no volunteers at 2 pm on a Tuesday," and the chief finds out when the tone drops and nobody answers. Turnout is a background agent for each department that polls volunteers by text each morning, forecasts which coverage gaps are dangerous using real call-pattern and weather data, closes gaps by nudging the right people, and, when it cannot, negotiates directly with neighboring departments' agents over the A2A protocol. The chief receives one text: "Thursday 10 to 2 is uncovered. Millbrook can cover with a 9-minute delay. Approve?" After a call, a 30-second voice debrief becomes a draft NERIS incident report. Certifications never lapse. Built with Strands Agents (Graph, agents-as-tools, A2A) and deployed on Amazon Bedrock AgentCore.
