/* Every InfoTip in one file, so the copy can be reviewed as copy.
   Rule: at most three short sentences. What it is, why it exists, and where to read more. */

window.INFOTIPS = {
  /* Domain terms ------------------------------------------------------- */
  second_due: "In the fire service, the second due is the company that arrives after the first, usually from a neighbouring department. It is the backup that shows up when the first crew cannot. The product is named for it.",
  mutual_aid: "A standing agreement between neighbouring departments to respond into each other's areas when needed. It is how most of rural America gets covered. Today it is arranged by one chief phoning another.",
  ambulance_desert: "A populated area more than 25 minutes from an ambulance station. Researchers at the Maine Rural Health Research Center mapped 4.5 million Americans living in one. See reference 2.",
  neris: "The National Emergency Response Information System. It replaced NFIRS on 1 February 2026 as the only national fire incident reporting system, so every department in the country moved to a new form this year. See reference 9.",
  turnout_time: "The minutes between a page going out and the apparatus leaving the station. It is added to travel time when a neighbouring department estimates how long it will take to arrive.",
  roll_call: "The morning question. One text to each member asking whether they can respond during a specific window. One character answers it.",
  district: "The part of a department's area a crew covers. Millbrook has a north and a south district; a gap is always tied to one of them.",
  min_crew: "The smallest qualified crew that can put an apparatus on the road. For an engine here it is one driver operator and two firefighters. A gap exists when the people available cannot make that crew.",

  /* Metrics ------------------------------------------------------------ */
  risk_score: "A number from 0 to 1 combining how many calls are expected, the chance nobody qualified responds, the weather, and how time-critical the calls in that window usually are. It runs as code, not as model reasoning, and every input is shown.",
  expected_calls: "Calls expected in this window, learned from this department's own 12 months of history by hour of day and day of week, then multiplied by any weather hazard. Departments with less than 90 days of history lean on a national-shaped profile, and the explanation says so.",
  p_understaffed: "The probability that the members who actually turn out cannot make the minimum crew. Per-member response probabilities come from their own history, with a prior of 32 percent, the middle of the 17 to 47 percent range reported for volunteer first responders. See reference 5.",
  hazard: "A multiplier from active National Weather Service alerts. An ice storm warning multiplies expected calls by 1.8, a red flag warning by 2.0. No alert means 1.0.",
  severity: "How time-critical the calls in this window usually are, from this department's own history. Cardiac, structure fire and entrapment weigh more than a service call. Scaled between 0.5 and 1.0.",
  interrupt_budget: "A hard limit on how many times the agent may interrupt the chief in a day. Research by Gloria Mark at UC Irvine found it takes about 23 minutes to recover focus after one interruption, so attention is treated as a budget and enforced in code, not by a prompt.",
  ledger: "Hours of mutual aid given and received between two departments. The agent prefers offers that keep the balance near zero, so no single department quietly becomes everyone's backup.",
  history_days: "How many days of this department's own call history the estimate is built from. Under 90 days, the model leans on a national-shaped profile and says so on the badge.",

  /* Agents -------------------------------------------------------------- */
  agent_rollcall: "Sends the morning poll and reads the replies. It understands Y, N, and plain English like 'till 2' or 'morning only', and honours STOP immediately.",
  agent_watch: "Recomputes coverage for the next seven days and scores every window that cannot make a crew. It calls the risk engine, which runs as real code.",
  agent_closer: "Tries to close a gap with our own members first, asking only the people most likely to say yes for that window, inside their quiet hours and weekly limit.",
  agent_neighbor: "Asks neighbouring departments over the Agent-to-Agent protocol and ranks their offers by delay, ledger balance, and the neighbour's own risk. It never confirms anything.",
  agent_chiefgate: "The only agent allowed to text the chief. It composes one message per decision, batches windows that share an answer, and respects the interrupt budget.",
  agent_scribe: "Turns a 30 second voice note into a draft NERIS incident report, and marks the fields it was not sure about instead of guessing.",
  agent_certclock: "Watches certification expiry dates and books the refresher before a card lapses and takes someone off the roster.",
  agent_coverage: "The agent a neighbouring department talks to. It answers coverage questions about its own department and nothing else. It cannot read our roster.",

  /* Protocol and platform ------------------------------------------------ */
  a2a: "The Agent-to-Agent protocol: an open standard for agents in different organizations to discover each other and exchange structured requests over HTTP. Each department runs its own agent, publishes an AgentCard describing what it can do, and keeps its own data.",
  agentcard: "A small JSON document at a well known URL describing what an agent can do. A neighbour reads it to learn that this department accepts coverage requests, before sending one.",
  strands_graph: "Strands Agents orchestration where each agent is a node and edges carry conditions. Turnout uses it because a safety workflow has to be deterministic and auditable: Watch, then Closer, then Neighbor, then Chief Gate, with each edge checking the store.",
  agentcore_runtime: "Hosts each department's agent in its own isolated sandbox with sessions that can stay open for hours, so an agent can wait for a member to reply without a server to babysit.",
  agentcore_memory: "Remembers which members say yes to which windows and how the chief likes decisions phrased, so the agent gets sharper every week without being retrained.",
  agentcore_gateway: "Turns the roster database, texting, weather and NERIS into tools the agents can call, with credentials kept out of agent code.",
  agentcore_identity: "Gives each agent scoped credentials to act for its own department, and to prove who it is to a neighbouring department's agent.",
  agentcore_code: "Runs the risk engine and the crew matching as real Python, with the inputs and outputs recorded. This is why the numbers on a gap card can be shown rather than asserted.",
  agentcore_observability: "Records every step the agents take as a trace. It is what the Trace tab reads, so a claim about what the system did can be checked rather than trusted.",
  hooks: "Strands hooks intercept a tool before it runs. Turnout uses them to enforce quiet hours and the weekly ask limit in code, so a policy about not bothering volunteers cannot be talked around by a prompt.",

  /* Product ------------------------------------------------------------- */
  judge_mode: "The demo runs with no login and no account. Press the steps in order to advance a simulated week. Everything you see is the real system running against synthetic data.",
  sandbox_key: "A public key that identifies your integration and applies a rate limit. It is scoped to the demo departments. In a real deployment each department has its own.",
  synthetic: "Millbrook, Riverton and Cedar Hollow are fictional. The members, phone numbers, twelve months of call history and the incident are all generated by a script in the repository.",
  weather_fixture: "The ice storm warning in this demo is injected by the scenario file so the same story plays every time. In a real deployment this tool calls the National Weather Service alerts API, which is public and needs no key.",
  quiet_hours: "Hours when a member will not be texted. Messages raised during quiet hours wait, and say so when they arrive. This is enforced by a hook in code.",
  held_message: "This message was raised during the member's quiet hours, so it waited until those hours ended before sending."
};
