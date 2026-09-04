"""Agent factories and the coverage Graph for one department.

The Graph runs as a pass, not a blocking loop: Watch -> Closer -> Neighbor -> Chief Gate, with edges
conditioned on what the store says. State lives in the store, so an hourly EventBridge trigger (or a
simulation tick) re-enters the Graph and picks up where the last pass left off.
"""

from __future__ import annotations

from strands import Agent
from strands.multiagent import GraphBuilder
from strands.multiagent.graph import GraphState

from turnout import runtime
from turnout.agents import prompts
from turnout.agents.hooks import hooks_for
from turnout.agents.models import fast_model, reasoning_model
from turnout.agents.peer_service import make_peer_tools
from turnout.models import ParsedReply
from turnout.tools.certs import find_expiring_certs, propose_training
from turnout.tools.chief import send_decisions, send_status
from turnout.tools.closer import check_asks, rank_candidates, send_ask
from turnout.tools.coverage import compute_coverage, get_gap, list_gaps, update_gap
from turnout.tools.ledger import get_ledger
from turnout.tools.neris import get_incident, save_neris_draft
from turnout.tools.peers import request_coverage_from_peers
from turnout.tools.roster import get_department, get_member_response_probability, list_members
from turnout.tools.sms import send_member_sms
from turnout.tools.weather import get_weather_alerts


NL2 = chr(10) * 2  # blank line between the preamble and the agent's own prompt


def _pre() -> str:
    r = runtime.get()
    d = r.store.get_department(r.dept_id)
    return prompts.preamble(d, r.clock.now().strftime("%A %Y-%m-%d %H:%M"))


def watch_agent() -> Agent:
    return Agent(name="Watch", description="Recomputes coverage and scores gaps.",
                 model=reasoning_model(), system_prompt=_pre() + "\n\n" + prompts.WATCH,
                 tools=[compute_coverage, get_weather_alerts, get_department], hooks=hooks_for("Watch"),
                 callback_handler=None)


def closer_agent() -> Agent:
    return Agent(name="Closer", description="Closes gaps with our own members first.",
                 model=reasoning_model(), system_prompt=_pre() + "\n\n" + prompts.CLOSER,
                 tools=[list_gaps, rank_candidates, send_ask, check_asks],
                 hooks=hooks_for("Closer"), callback_handler=None)


def neighbor_agent() -> Agent:
    return Agent(name="Neighbor", description="Negotiates mutual aid with peer departments over A2A.",
                 model=reasoning_model(), system_prompt=_pre() + "\n\n" + prompts.NEIGHBOR,
                 tools=[list_gaps, get_gap, request_coverage_from_peers, get_ledger],
                 hooks=hooks_for("Neighbor"), callback_handler=None)


def chief_gate_agent() -> Agent:
    return Agent(name="ChiefGate", description="Sends the chief exactly one decision text per gap.",
                 model=reasoning_model(), system_prompt=_pre() + "\n\n" + prompts.CHIEF_GATE,
                 tools=[list_gaps, get_gap, send_decisions, send_status], hooks=hooks_for("ChiefGate"),
                 callback_handler=None)


def scribe_agent() -> Agent:
    return Agent(name="Scribe", description="Drafts NERIS reports from voice debriefs.",
                 model=reasoning_model(), system_prompt=_pre() + "\n\n" + prompts.SCRIBE,
                 tools=[get_incident, save_neris_draft], hooks=hooks_for("Scribe"), callback_handler=None)


def cert_clock_agent() -> Agent:
    return Agent(name="CertClock", description="Keeps certifications from lapsing.",
                 model=reasoning_model(), system_prompt=_pre() + "\n\n" + prompts.CERT_CLOCK,
                 tools=[find_expiring_certs, propose_training, list_members], hooks=hooks_for("CertClock"),
                 callback_handler=None)


def coverage_peer_agent(rt=None) -> Agent:
    """The agent a neighbouring department talks to over A2A.

    Its tools are bound to one department's runtime, so two departments served from the same process
    never read each other's data.
    """
    rt = rt or runtime.get()
    d = rt.store.get_department(rt.dept_id)
    pre = prompts.preamble(d, rt.clock.now().strftime("%A %Y-%m-%d %H:%M"))
    return Agent(name="Coverage",
                 description="Answers mutual aid coverage requests from neighbouring departments.",
                 model=fast_model(), system_prompt=pre + NL2 + prompts.COVERAGE_PEER,
                 tools=make_peer_tools(rt), hooks=hooks_for("Coverage"), callback_handler=None)


def roll_call_parse(text: str, window_desc: str, purpose: str) -> ParsedReply:
    """Model-backed parse for replies the rule parser could not read."""
    agent = Agent(name="RollCall", model=fast_model(), system_prompt=_pre() + "\n\n" + prompts.ROLL_CALL,
                  callback_handler=None)
    return agent.structured_output(
        ParsedReply, f"Last message purpose: {purpose}. Window asked about: {window_desc}. Member replied: {text!r}"
    )


# Graph edge conditions read the store, not the previous node's prose.

def _gaps(statuses: set[str], levels: set[str]) -> list:
    r = runtime.get()
    now = r.clock.now()
    return [g for g in r.store.list_gaps(r.dept_id, statuses) if g.level.value in levels and g.window_end > now]


def needs_closer(_: GraphState) -> bool:
    return bool(_gaps({"open", "asking_members"}, {"high", "critical"}))


def needs_neighbor(_: GraphState) -> bool:
    return bool(_gaps({"members_declined"}, {"high", "critical"}))


def needs_chief(_: GraphState) -> bool:
    r = runtime.get()
    now = r.clock.now()
    return any(g.decision_sent_at is None for g in r.store.list_gaps(r.dept_id, {"needs_chief", "no_options"})
               if g.window_end > now)


def build_coverage_graph():
    b = GraphBuilder()
    b.add_node(watch_agent(), "watch")
    b.add_node(closer_agent(), "closer")
    b.add_node(neighbor_agent(), "neighbor")
    b.add_node(chief_gate_agent(), "chief_gate")
    b.add_edge("watch", "closer", condition=needs_closer)
    b.add_edge("closer", "neighbor", condition=needs_neighbor)
    b.add_edge("neighbor", "chief_gate", condition=needs_chief)
    b.add_edge("closer", "chief_gate", condition=lambda s: needs_chief(s) and not needs_neighbor(s))
    b.set_entry_point("watch")
    b.set_max_node_executions(8)
    b.set_execution_timeout(600)
    return b.build()


def run_coverage_pass(reason: str = "scheduled") -> dict:
    """One pass of the coverage Graph for the active department."""
    r = runtime.get()
    r.emit("graph_start", reason=reason)
    graph = build_coverage_graph()
    result = graph(f"Coverage pass ({reason}). Do your job and report briefly.")
    summary = {"status": str(result.status), "order": [n.node_id for n in result.execution_order],
               "outputs": {}}
    for node_id, node_result in result.results.items():
        try:
            summary["outputs"][node_id] = str(node_result.result)[:800]
        except Exception:
            summary["outputs"][node_id] = "?"
    r.emit("graph_end", **summary)
    return summary
