# Turnout: Landing Page Specification

Follows `DESIGN_SYSTEM.md`. This file contains final copy. Every domain term and every metric has an InfoTip; the InfoTip text is given inline as `[i: ...]`.

Accent: engine red (`#B3261E` light, `#F26D63` dark). Hero imagery: a quiet station bay, daylight, one engine, no people. In dark mode, the same bay at dusk with the bay lights on.

---

## Header

Left: wordmark "Turnout". Center (desktop) or menu (mobile): Live demo, How it works, For judges, Developers, References. Right: theme toggle (Light, Dark, System), "Try the live demo" button.

---

## Section 1: Hero

Heading (h1): **Every other tool tells the chief who is coming. Turnout makes sure someone is.**

Subheading: A background agent for volunteer fire and EMS departments. It finds the hours when nobody can respond, fills them by asking the right people and the right neighbors, and interrupts the chief only for the one decision that needs a human.

Buttons: "Try the live demo" (primary), "Watch the 4-minute video" (secondary).

Under the buttons, a muted looping recording (12 seconds): the Station Board shows a red Thursday window, a text goes to the chief, the chief taps 1, the window turns green, and the Network View shows Riverton's edge light up.

Credibility line: "4.5 million Americans live more than 25 minutes from an ambulance [i: Maine Rural Health Research Center, 2023. Ambulance deserts are populated areas not reachable within 25 minutes of a stationed ambulance.] · Built on peer-reviewed volunteer response research [i: We use the response-probability model from the 2023 Predictive Dispatch study and formal understaffing models from Transportation Research Part E. See References.] · Runs on Amazon Bedrock AgentCore [i: AgentCore hosts, secures, and observes the agents. See the architecture section.]"

---

## Section 2: The problem

Heading: **The station is not empty. It is empty at 2 pm on a Tuesday.**

Intro: Two-thirds of America's firefighters are volunteers. Most rural ambulances are staffed by volunteers. They work day jobs, often 30 miles from the station. The roster looks fine on paper and is empty in the middle of the workday, and the chief finds out when the tone drops and nobody answers.

Three stat cards:

1. **35-year low.** Volunteer firefighter numbers hit a 35-year low in 2020 while calls more than tripled. [i: National Fire Protection Association, NFPA Journal, February 2026. Reference 1.]
2. **13 minutes vs 6.** Median rural EMS response is 13 minutes, versus 6 in cities and suburbs, across 1.8 million runs. [i: Mell and colleagues, JAMA Surgery, 2017. Reference 3.]
3. **5 to 12 percent per minute.** Survival from cardiac arrest drops that much for every minute of delay. [i: Journal of the American Heart Association, 2020. Reference 4.]

Story block (two sentences, italic): Chief Dana Ortiz runs Millbrook Volunteer Fire Company and a hardware store. On Wednesday night she will send the same text to 14 people, call two neighboring chiefs, and still not know who is covering Thursday morning.

Time line: In the demo, closing one critical gap by hand takes the chief about 40 minutes of texting and calling. With Turnout it takes one text and eight seconds. [i: Measured in the demo scenario. We do not put a dollar value on a volunteer chief's time; the point is the minutes, and the calls that happen during them.]

Secondary line: Mutual aid, the practice of neighboring departments covering for each other [i: Mutual aid is a formal or informal agreement between departments to respond into each other's territory when needed. It is how rural America survives, and it is arranged by phone.], is how the gap gets filled today. It lands unevenly: some departments become hubs and burn out. [i: Capital Area Fire Districts Association analysis. Reference 8.]

---

## Section 3: How it works

Heading: **The chief keeps every decision. The agent does the chasing.**

Four steps, each with an illustration, one line, and an InfoTip.

1. **Roll call by text.** Each morning, one message per volunteer: "Around Thu 8a to 5p? Y or N." No app. [i: Roll Call is a Strands agent that sends the poll and reads replies, including free text like "till 2." Volunteers can reply STOP at any time.]
2. **It sees the hole before it hurts.** The agent forecasts which uncovered hours are dangerous using the department's own call history, who is likely to actually respond, and the weather. [i: The Watch agent calls a deterministic risk engine that runs as code. It reports expected calls, the chance no qualified crew responds, and any weather hazard, and shows you the numbers.]
3. **It closes the hole itself, then calls the neighbors.** First it asks the members most likely to say yes. If that fails, its agent talks directly to the neighboring departments' agents. [i: The Neighbor agent uses the Agent-to-Agent protocol, an open standard for agents in different organizations to exchange structured requests. Each department runs its own agent and controls its own data.]
4. **One text to the chief.** "Thursday 10 to 2: critical. Riverton can cover, 9-minute delay. Approve?" One tap. [i: The Chief Gate agent composes exactly one message and waits. Nothing is confirmed with a neighbor until the chief approves.]

Below the steps, two smaller cards:

- **After the call, the report writes itself.** A 30-second voice note in the truck becomes a draft NERIS incident report. [i: NERIS is the National Emergency Response Information System. It replaced NFIRS as the only national fire incident data system on February 1, 2026. Reference 9.]
- **Nobody's certification lapses.** The agent schedules required training months before a card expires. [i: Most states require about 24 hours of annual training to keep a firefighter certification current. A lapsed card removes a member from the roster.]

---

## Section 4: See it happen

Heading: **Play the week.**

Embedded demo frame with "Judge mode" preselected. A short instruction line: "You are Chief Ortiz. Press Play the week. Watch the Station Board, then check your phone on the right." Buttons: "Open full demo", "Reset scenario".

Beneath: three tabs, Station Board, Network View, Trace Viewer, each with a screenshot in the current theme and an InfoTip. [i for Trace Viewer: Every step the agents take is recorded with Amazon Bedrock AgentCore Observability. You can see the risk numbers, the messages sent, and the exchange with Riverton's agent.]

---

## Section 5: What makes it different

Heading: **Three things no scheduling app does.**

1. **Agents that are good neighbors to each other.** Each department's agent negotiates coverage directly with neighboring departments' agents, and a shared ledger keeps the network fair over a season. [i: The mutual aid ledger records hours given and received between each pair of departments. The Neighbor agent prefers offers that keep balances near zero.]
2. **A risk engine you can read.** Not "the AI considered the weather." Real numbers from your own call history, published response-probability research, and live National Weather Service alerts, shown on every gap. [i: The formula is documented in the repository and on the Developers page.]
3. **No app for volunteers.** A phone number works on every phone, for every member, with zero setup. The chief has a dashboard. Everyone else has a text.

Honest comparison block, heading "What about the tools that exist?":

IamResponding, Aladtec, First Due, and others are good at showing who is responding after a page and at scheduling paid shifts. They do not find the gap before it exists, negotiate with the next town, or run on a volunteer department's budget. Turnout is designed to sit beside them, and its API can feed them.

---

## Section 6: Built on Strands Agents and AgentCore

Heading: **Seven agents, three departments, one protocol.**

Interactive architecture diagram (SVG, light and dark). Clickable nodes with InfoTips:

- Strands Graph [i: Strands Agents SDK orchestration where agents are nodes and edges carry conditions. We use it because a safety workflow must be deterministic and auditable. The loop from Closer back to Watch is bounded.]
- Roll Call, Watch, Closer, Neighbor, Chief Gate, Scribe, Cert Clock [i for each: one sentence on role]
- A2A [i: Agent-to-Agent protocol. Each department publishes an AgentCard describing what it can do and accepts structured coverage requests from trusted peers.]
- AgentCore Runtime [i: Hosts each department's agent in isolation with long-running sessions, so the agent can wait for replies for an hour without a server to manage.]
- AgentCore Memory [i: Remembers which members usually say yes to which windows and how the chief likes decisions phrased, so the agent gets sharper every week.]
- AgentCore Gateway [i: Turns the roster database, SMS, weather, and NERIS into tools the agents can call, with credentials kept out of agent code.]
- AgentCore Identity [i: Gives each agent scoped credentials to act for its department and to prove its identity to peer departments.]
- AgentCore Code Interpreter [i: Runs the risk engine and crew-matching math as real code, with inputs and outputs logged.]
- AgentCore Observability [i: Records every step as a trace you can inspect in the Trace Viewer.]

Link: "Read the technical design" to the repo docs.

---

## Section 7: For judges

Heading: **Everything the rubric asks for, in one place.**

A five-row checklist matching the criteria in order. Each row: criterion name, one sentence on how the project addresses it, and evidence links.

| Criterion | Evidence |
|---|---|
| Technical Implementation | Repo · Live demo · Trace Viewer · Eval results · CDK stacks · AgentCore services used (list) |
| Design | Landing page · Station Board · Simulated phones · Light and dark toggle · Accessibility report |
| Potential Impact | The problem section · References · The demo scenario walkthrough |
| Creativity and Originality | A2A mutual aid network · Readable risk engine · No-app design · Positioning against existing tools |
| Presentation | The video · Transcript · Architecture diagram |

Plus: "Blog posts on builder.aws.com" with the three links, and "License: MIT, visible in the repository About section."

---

## Section 8: For developers

Heading: **Use it from your own systems.**

Quickstart in three commands (clone, `make demo`, open localhost). Sandbox API key shown with a copy button and a note that it is scoped to the demo departments. Four example requests with curl: push availability, get coverage, submit a decision, upload a debrief. Link to OpenAPI. Link to the A2A AgentCard for Millbrook so developers can see the protocol surface.

InfoTip on "API key" [i: A key identifies your integration and applies a rate limit. The sandbox key is public and limited to the demo data.]

---

## Section 9: Safety and limits

Heading: **What it will never do.**

- It never pages anyone to an incident. Dispatch stays with dispatch.
- It never confirms mutual aid without a chief's approval, unless that chief has set a narrow auto-approval rule.
- It never texts a volunteer during their quiet hours or more than the weekly limit. This is enforced in code, not by a prompt.
- It never stores location, health, or personal data beyond name, phone, roles, certifications, availability, and response history.
- It never submits a NERIS report on its own. The chief reviews and presses submit.

---

## Section 10: References

1. NFPA Journal, "Volunteer Fire Service Crisis: U.S. Departments Struggle with Staffing Amid Growing Call Volume," February 11, 2026.
2. Maine Rural Health Research Center, "Ambulance Deserts: Geographic Disparities in the Provision of Ambulance Services," 2023.
3. Mell HK et al., "Emergency Medical Services Response Times in Rural, Suburban, and Urban Areas," JAMA Surgery, 2017.
4. "Shortening Ambulance Response Time Increases Survival in Out-of-Hospital Cardiac Arrest," Journal of the American Heart Association, 2020.
5. "Predictive Dispatch of Volunteer First Responders: Algorithm Development and Validation," 2023 (PMC10716760).
6. "Planning for time-varying volunteer firefighter systems under probabilistic service disruptions," Transportation Research Part E, 2021.
7. FireRescue1, "Volunteer fire departments face rising call volumes and staffing challenges in rural Missouri."
8. Capital Area Fire Districts Association, "The Greatest Threat Facing the Volunteer Fire Service is Math, Not Recruitment."
9. US Fire Administration, "NFIRS Sunset" and NERIS documentation, 2026.
10. Vermont Division of Fire Safety, Firefighter Certification requirements (representative state rule).
11. Strands Agents SDK documentation: Graph, Agent-to-Agent protocol.
12. Amazon Bedrock AgentCore documentation.

---

## Footer

MIT License · GitHub repository · Contact · Theme toggle · "Built for the AWS Agents for Humans Hackathon, September 2026. Millbrook, Riverton, and Cedar Hollow are fictional departments; all data is synthetic."
