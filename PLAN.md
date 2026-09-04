# Turnout: Product Plan

## 1. The problem, precisely

### 1.1 Who is affected

Volunteer fire departments and volunteer or combination EMS agencies in small towns and rural counties. In the United States, roughly two-thirds of firefighters are volunteers, and 74 percent of volunteer EMS professionals serve rural communities. A typical department in this segment has 12 to 40 members, a chief with a day job, an annual budget under 100 thousand dollars, and no administrative staff.

The people inside the problem:

- The chief. Runs the department on nights and weekends. Spends hours each week texting members to ask who can cover, calling neighboring chiefs to arrange backup, chasing training records, and filing incident reports.
- The volunteers. Want to serve, but work 30 miles away during the day and are asked the same question ("can you cover Thursday?") in three different group chats.
- The neighboring chief. Gets a call at 6 am asking for coverage, when their own department is no better off.
- The resident. Has a heart attack at 2 pm on a Tuesday and does not know that the station two miles away is empty.

### 1.2 The evidence

| Fact | Source |
|---|---|
| Volunteer firefighter numbers reached a 35-year low in 2020 while call volume more than tripled over the same period. | NFPA Journal, "Volunteer Fire Service Crisis," February 2026. https://www.nfpa.org/news-blogs-and-articles/nfpa-journal/2026/02/11/volunteer-fire-service-crisis |
| 4.5 million Americans live in an "ambulance desert," defined as more than 25 minutes from a stationed ambulance; 2.3 million of them in rural counties. Rural residents are 14 percent of the population but more than half of ambulance-desert residents. | Maine Rural Health Research Center, "Ambulance Deserts: Geographic Disparities in the Provision of Ambulance Services," 2023. https://www.ruralhealthresearch.org/publications/1596 |
| Median EMS response time is 13 minutes in rural areas versus 6 minutes in urban and suburban areas, across 1.8 million EMS runs. One in ten rural calls waits nearly 30 minutes. | Mell et al., JAMA Surgery, 2017. https://jamanetwork.com/journals/jamasurgery/fullarticle/2643992 |
| Survival from out-of-hospital cardiac arrest falls by roughly 5 to 12 percent per minute of delay in response. | Journal of the American Heart Association, 2020. https://www.ahajournals.org/doi/10.1161/JAHA.120.017048 |
| Volunteer first responders respond to alerts only 17 to 47 percent of the time; a model using event data, demographics, and prior response history predicted individual response with 79.1 percent accuracy. | "Predictive Dispatch of Volunteer First Responders," JMIR / PMC, 2023. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10716760/ |
| Formal models exist for volunteer fire systems where service is disrupted by time-varying understaffing. | "Planning for time-varying volunteer firefighter systems under probabilistic service disruptions," Transportation Research Part E, 2021. https://www.sciencedirect.com/science/article/abs/pii/S1366554521002234 |
| Departments report as many as 18 responders on a weekday evening and only a handful during the workday. Employers no longer release workers for calls. | FireRescue1, rural Missouri reporting. https://www.firerescue1.com/volunteer-fire-service/rural-mo-volunteer-fire-departments-face-rising-call-volumes-staffing-challenges |
| Mutual aid fills gaps unevenly; some departments become hubs and others dependent, and hubs burn out. | Capital Area Fire Districts Association, "The Greatest Threat Facing the Volunteer Fire Service is Math." https://cafda.net/the-greatest-threat-facing-the-volunteer-fire-service-is-math-not-recruitment-this-is-a-must-read-article/ |
| NERIS replaced NFIRS as the only national fire incident reporting system on February 1, 2026. Every department must now file into a new system. | US Fire Administration, NFIRS sunset. https://www.usfa.fema.gov/nfirs/sunset/ |
| Certification renewal typically requires 24 hours of annual continuing training; lapses remove a member from the response roster. | Vermont Division of Fire Safety certification rules (representative). https://firesafety.vermont.gov/academy/certification |

### 1.3 The mechanism we target

The failure is not tally. It is the **daytime coverage gap**: a predictable, recurring window when the roster on paper is fine and the roster in reality is empty. Chiefs manage this by hand with group texts and phone calls, which does not scale, burns them out, and leaves the mutual aid burden landing on whichever neighbor is kindest.

Turnout automates the chasing and makes the network of neighbors self-balancing. The chief keeps every decision that matters.

---

## 2. The product

### 2.1 One sentence

Turnout is a background agent for each volunteer department that finds dangerous coverage gaps before they happen, closes them by asking the right people and the right neighbors, and interrupts the chief only for the one decision that needs a human.

### 2.2 What the chief experiences

- Morning: nothing. The agent already asked everyone.
- Midday: one text, only if there is a gap the agent could not close on its own. One tap to approve.
- After a call: a 30-second voice note in the truck. The incident report drafts itself.
- Monthly: nothing. Certifications are tracked and training is scheduled before anything expires.

### 2.3 What a volunteer experiences

- One text per day, sometimes fewer: "Around Thu 8a to 5p? Reply Y or N." One character to reply.
- Occasional targeted asks when they are the best fit, never more than a set number per week, never during their quiet hours.
- Recognition: a monthly summary of hours covered.

### 2.4 What the neighboring department experiences

- Their agent receives a structured request from ours, checks their own coverage, and answers. Their chief only sees requests that need approval.
- A shared ledger tracks who covered whom. The network balances over a season.

---

## 3. Scope

### 3.1 In scope for the submission

| Feature | Description | Priority |
|---|---|---|
| Roll Call | Daily availability poll by SMS with one-character replies; parses free text too ("can do till 2") | Must |
| Coverage Watch | Hourly coverage map for the next 7 days per district, with crew-qualification logic (driver, firefighter, EMT) | Must |
| Risk Engine | Deterministic risk score per window using call-history rates, per-volunteer response probability, weather hazard multipliers, and severity weighting; explains its math | Must |
| Closer | Targeted asks to volunteers most likely to say yes; proposes swaps; respects quiet hours and weekly ask limits | Must |
| Neighbor (A2A) | Requests coverage from neighboring departments' agents over A2A; evaluates offers by response delay and ledger balance; presents the best offer | Must |
| Chief Gate | Single decision message; approve, decline, or ask for alternatives; executes the approved plan | Must |
| Mutual Aid Ledger | Tracks coverage given and received; visible to both chiefs | Must |
| Scribe | Voice debrief to draft NERIS incident report; chief reviews and submits | Must |
| Cert Clock | Certification expiry tracking; schedules training; nudges members | Must |
| Station Board (web) | Chief's dashboard: coverage heatmap, gaps, decisions, ledger, traces | Must |
| Network View (web) | Map of the three demo departments with live A2A negotiation animation | Must |
| Trace Viewer (web) | Embedded AgentCore Observability trace for the current scenario | Must |
| Simulated Phones (web) | In-browser phones for the chief and volunteers so judges can play both sides without real SMS | Must |
| Real SMS | Two-way SMS via AWS End User Messaging for the demo phone number | Should |
| Public API with keys | Departments and integrators can push availability and pull coverage | Should |
| NERIS submission via AgentCore Browser | Fill the NERIS web form when no API is available | Could |
| Weather-triggered pre-staging suggestions | "Ice storm Tuesday; consider staffing the station 6 to 10 am" | Could |

### 3.2 Explicitly out of scope

- Dispatch. Turnout does not receive 911 calls or page crews. It works alongside dispatch, not instead of it.
- Payroll, stipends, or LOSAP point calculations.
- Apparatus maintenance tracking.
- Real integration with any CAD vendor. The API is designed so a CAD integration is possible later.

---

## 4. Positioning against existing tools

| Tool | What it does | What it does not do | Our one-sentence answer |
|---|---|---|---|
| IamResponding | Shows who is responding after a page; scheduling; expiration tracking | Does not find gaps before they happen or fill them; no cross-department negotiation | "IamResponding shows the roster after the tone drops. Turnout fills it before." |
| First Due (AI scheduling) | Enterprise scheduling with predictive staffing suggestions for one department | No SMS-only workflow, no mutual aid negotiation, no stated volunteer focus, enterprise pricing | "First Due schedules one department. Turnout is the network between departments, on a volunteer budget and a flip phone." |
| Aladtec, Vector Scheduling, ImageTrend | Career department scheduling and records | Built for paid shifts and overtime rules | "Those manage paid shifts. Turnout manages a volunteer's Tuesday afternoon." |
| Group texts and phone calls | What most volunteer chiefs actually use | Everything | "This is the job Turnout takes off the chief's plate." |

We say this plainly on the landing page. Judges respect an honest comparison more than a claim of no competitors.

---

## 5. Why it wins each criterion

| Criterion | How Turnout reaches the ceiling |
|---|---|
| Technical Implementation | Strands Graph with conditional edges and a bounded loop inside each department; agents-as-tools for Scribe and Cert; A2A server and client between departments with AgentCard discovery; AgentCore Runtime (three instances), Memory, Gateway, Identity, Code Interpreter, Observability. Live URL. CDK. Tests and evals. |
| Design | A complete product: landing page, chief dashboard, volunteer SMS flow, neighbor view, API docs, InfoTips everywhere, light and dark, mobile and desktop. Nothing is a mock. |
| Potential Impact | Ten cited sources. A quantified audience (4.5 million in ambulance deserts, thousands of volunteer departments). The demo shows a real-shaped gap being closed and the chief's decision taking eight seconds instead of forty minutes. |
| Creativity and Originality | The A2A mutual aid network: Good Neighbor agents that are literally good neighbors to each other. A deterministic risk engine inside an agent, cited to the volunteer-response literature. A product that has no app for volunteers. Insider vocabulary used correctly. |
| Presentation | A 4:15 video that opens on an empty station at 2:14 pm, shows the agent working from a real deployment, and ends on one text and a truck rolling from the next town. |

---

## 6. Success criteria for the build

Measured on the synthetic three-department dataset described in `DEMO_AND_VIDEO.md`.

| Metric | Target |
|---|---|
| Gaps detected out of planted gaps | 100 percent (deterministic) |
| Critical gaps closed without chief involvement | at least 60 percent |
| Critical gaps closed with one chief decision | at least 95 percent |
| Chief interrupts per week in the demo scenario | at most 3 |
| Volunteer texts per person per week | at most 7 (one poll per day) plus at most 2 targeted asks |
| Roll Call reply parsing accuracy on the eval set (200 messages) | at least 97 percent |
| NERIS draft field accuracy on 20 voice debriefs | at least 90 percent of required fields correct |
| A2A round trip for a coverage request | under 8 seconds |
| Landing page Lighthouse | Performance 95, Accessibility 100 |

---

## 7. Safety, ethics, and trust

- Nothing binding happens without a human. Mutual aid commitments require chief approval on both sides unless a chief has explicitly enabled auto-approval for a bounded case (for example, delay under 10 minutes and ledger balance within 5 hours).
- Volunteers control their contact. Quiet hours, weekly ask limits, and a one-word opt-out ("STOP") are honored immediately.
- Minimal data. Name, phone, qualifications, certification dates, availability, and response history. No location tracking. No health data.
- Explainable decisions. Every gap message states the numbers behind the risk level.
- No black-box dispatch. The agent never pages anyone to an incident.
- Data residency. Each department's data lives in its own AWS account when self-hosted; the demo runs in ours.
- The system is explicitly described as decision support for the chief, not a replacement for the chief.

---

## 8. Naming and language

- Product name: Turnout.
- Agent names use fire-service words: Roll Call, Watch, Closer, Neighbor, Chief Gate, Scribe, Cert Clock.
- Demo departments: Millbrook Volunteer Fire Company, Riverton Fire and Rescue, Cedar Hollow Volunteer Fire Department. All fictional.
- We never call it "AI dispatch." We call it "coverage."
