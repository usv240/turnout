"""The demo service: one process holding the three departments and driving the simulated week.

The web app talks to this. Judge mode drives it with no login. A sandbox API key gives the same
read access to anyone who wants to call it from their own code.
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta
from typing import Any

from turnout import runtime
from turnout.agents.department import run_coverage_pass
from turnout.agents.roll_call import handle_inbound, send_daily_polls
from turnout.models import Incident
from turnout.sim.runner import setup
from turnout.tools.sms import flush_held

SCENARIO = "data/scenarios/demo_week.json"

STEPS: list[dict[str, Any]] = [
    {"id": "poll", "at": "2026-09-09T06:30", "title": "Roll call",
     "detail": "One text to each of the 14 members, asking about Thursday."},
    {"id": "watch", "at": "2026-09-09T07:30", "title": "Coverage pass",
     "detail": "Replies are in. Watch scores the week, and Closer asks the two best candidates."},
    {"id": "neighbors", "at": "2026-09-09T08:45", "title": "Ask the neighbours",
     "detail": "Members cannot cover it. Neighbor asks Riverton and Cedar Hollow over A2A, and Chief "
               "Gate sends the chief one text."},
    {"id": "approve", "at": "2026-09-09T09:15", "title": "The chief decides",
     "detail": "The chief replies 1. Riverton is confirmed and the ledger moves."},
    {"id": "incident", "at": "2026-09-10T13:00", "title": "After the call",
     "detail": "A collision on Thursday. The officer leaves a voice note and Scribe drafts the report."},
]


def hour_label(dt: datetime) -> str:
    suffix = "am" if dt.hour < 12 else "pm"
    return f"{dt.hour % 12 or 12}{suffix}"


def window_label(g) -> str:
    return f"{g.window_start:%A} {hour_label(g.window_start)} to {hour_label(g.window_end)}"


class DemoService:
    """Holds one runtime and advances it. Locked, because the web app serves many viewers."""

    def __init__(self, scenario: str = SCENARIO) -> None:
        self.scenario = scenario
        self.lock = threading.RLock()
        self.reset()

    def reset(self) -> dict:
        with self.lock:
            self.rt, self.sc = setup(self.scenario)
            self.rt.dept_id = "millbrook"
            runtime.configure(self.rt)
            self.done: list[str] = []
            return self.state()

    def _tick_to(self, when: datetime) -> None:
        while self.rt.clock.now() < when:
            minutes = int((when - self.rt.clock.now()).total_seconds() // 60)
            self.rt.clock.advance(minutes=min(15, max(1, minutes)))
            flush_held(self.rt)
            self.rt.sms.deliver_due()
            self.rt.dept_id = "millbrook"

    def step(self, step_id: str | None = None) -> dict:
        """Run the next step of the demo week, or a named one."""
        with self.lock:
            remaining = [s for s in STEPS if s["id"] not in self.done]
            if step_id:
                target = next((s for s in STEPS if s["id"] == step_id), None)
            else:
                target = remaining[0] if remaining else None
            if target is None:
                return {"ran": None, **self.state()}
            self._tick_to(datetime.fromisoformat(target["at"]))
            runtime.configure(self.rt)
            self.rt.dept_id = "millbrook"

            if target["id"] == "poll":
                send_daily_polls()
            elif target["id"] in ("watch", "neighbors"):
                run_coverage_pass(target["id"])
            elif target["id"] == "approve":
                self._tick_to(datetime.fromisoformat(target["at"]) + timedelta(minutes=10))
                run_coverage_pass("after the chief decided")
            elif target["id"] == "incident":
                self._run_incident()

            if target["id"] not in self.done:
                self.done.append(target["id"])
            return {"ran": target["id"], **self.state()}

    def _run_incident(self) -> None:
        from turnout.agents.department import scribe_agent

        inc = self.sc["incident"]
        at = datetime.fromisoformat(inc["at"])
        district = inc["district"]
        self.rt.store.put_incident(Incident(id="inc-0001", dept_id="millbrook", at=at,
                                            transcript=inc["voice_note"]))
        self.rt.emit("voice_note", incident_id="inc-0001", transcript=inc["voice_note"])
        scribe_agent()(f"Draft the NERIS report for incident inc-0001. Dispatch was {at:%H:%M}, "
                       f"district {district}, Riverton covered under mutual aid.")

    def reply(self, phone: str, body: str) -> dict:
        with self.lock:
            runtime.configure(self.rt)
            return {"handled": handle_inbound(phone, body), **self.state()}

    def state(self) -> dict:
        r = self.rt
        d = r.store.get_department("millbrook")
        gaps = [g for g in r.store.list_gaps("millbrook") if g.window_end > r.clock.now()]
        actionable = [g for g in gaps if g.status != "thin"]
        waiting = [g for g in actionable if g.status in ("needs_chief", "no_options") and g.decision_sent_at]
        worst = max((g for g in actionable if g.status != "covered"),
                    key=lambda g: g.risk_score, default=None)
        if waiting:
            headline = f"1 gap needs you. {window_label(waiting[0])}."
            tone = "needs_you"
        elif worst is not None:
            headline = f"{worst.level.value.capitalize()} gap. {window_label(worst)}. Working on it."
            tone = "working"
        else:
            headline = "All windows covered through Sunday."
            tone = "clear"
        return {
            "now": r.clock.now().isoformat(),
            "department": {"id": d.id, "name": d.name, "short_name": d.short_name,
                           "districts": d.districts, "chief_phone": d.chief_phone},
            "headline": headline,
            "tone": tone,
            "interrupts": self.interrupts(),
            "steps": [{**s, "done": s["id"] in self.done} for s in STEPS],
            "gaps": [self.gap_json(g) for g in sorted(gaps, key=lambda g: (g.window_start, -g.risk_score))],
            "ledger": [{"peer": p, "peer_name": r.store.get_department(p).short_name,
                        "balance_hours": r.store.ledger_balance("millbrook", p)} for p in d.peers],
            "members": [{"id": m.id, "name": m.name, "phone": m.phone,
                         "roles": [x.value for x in m.roles], "opted_out": m.opted_out,
                         "asks_this_week": m.asks_this_week, "quiet_hours": list(m.quiet_hours)}
                        for m in r.store.list_members("millbrook")],
            "incidents": [{"id": i.id, "at": i.at.isoformat(), "status": i.status,
                           "transcript": i.transcript,
                           "draft": i.draft.model_dump(mode="json") if i.draft else None}
                          for i in r.store.list_incidents("millbrook")],
        }

    def interrupts(self) -> dict:
        from turnout.tools.chief import DAILY_INTERRUPT_BUDGET

        r = self.rt
        d = r.store.get_department("millbrook")
        today = r.clock.now().date()
        used = sum(1 for m in r.store.list_messages("millbrook", d.chief_phone)
                   if m.direction == "out" and m.purpose in ("decision", "escalation")
                   and m.at.date() == today)
        return {"used_today": used, "budget": DAILY_INTERRUPT_BUDGET}

    def gap_json(self, g) -> dict:
        return {
            "id": g.id,
            "window": f"{g.window_start:%a} {g.window_start:%H:%M}-{g.window_end:%H:%M}",
            "window_label": window_label(g),
            "day": f"{g.window_start:%A}",
            "start": g.window_start.isoformat(), "end": g.window_end.isoformat(),
            "district": g.district, "level": g.level.value, "risk_score": g.risk_score,
            "explanation": g.explanation, "status": g.status, "covered_by": g.covered_by,
            "resolution": g.resolution, "asked": g.asked_member_ids,
            "missing_roles": [x.value for x in g.inputs.missing_roles],
            "inputs": {"expected_calls": g.inputs.expected_calls, "p_understaffed": g.inputs.p_understaffed,
                       "hazard": g.inputs.hazard, "hazard_names": g.inputs.hazard_names,
                       "severity": g.inputs.severity, "history_days": g.inputs.history_days,
                       "available_member_ids": g.inputs.available_member_ids,
                       "ran_in": g.inputs.ran_in},
            "offers": [{"peer": o.from_dept,
                        "peer_name": self.rt.store.get_department(o.from_dept).short_name,
                        "can_cover": o.can_cover, "delay_min": o.estimated_delay_min,
                        "ledger_delta_hours": o.ledger_delta_hours, "reason": o.reason_if_declined,
                        "peer_risk": o.peer_current_risk, "auto_approved": o.auto_approved}
                       for o in g.offers],
        }

    def messages(self, phone: str | None = None) -> list[dict]:
        return [{"at": m.at.isoformat(), "to": m.to, "member_id": m.member_id, "direction": m.direction,
                 "body": m.body, "purpose": m.purpose, "held": m.held_for_quiet_hours}
                for m in self.rt.store.list_messages("millbrook", phone)]

    def crew(self) -> dict:
        """What the agent knows about each member, and what it has asked of them.

        A scheduling agent asks real people for real hours of their life. Everything it uses to
        decide who to ask is here, in the words the member would use: how often it has already
        asked this week, when it will not text them, and how often they have said yes before. If a
        person cannot see that, they cannot argue with it.
        """
        from turnout.engine.kernel import response_probability
        from turnout.tools.chief import DAILY_INTERRUPT_BUDGET

        r = self.rt
        d = r.store.get_department("millbrook")
        messages = self.messages()
        out = []
        for m in r.store.list_members("millbrook"):
            mine = [x for x in messages if x["member_id"] == m.id]
            stats = []
            for window, st in sorted(m.response_stats.items()):
                stats.append({"window": window, "yes": st.yes, "no": st.no,
                              "probability": round(response_probability(st.yes, st.no), 3)})
            yes = sum(x.yes for x in m.response_stats.values())
            no = sum(x.no for x in m.response_stats.values())
            out.append({
                "id": m.id, "name": m.name, "phone": m.phone,
                "roles": [x.value for x in m.roles],
                "certs": [{"type": c.type, "expires": c.expires.date().isoformat()}
                          for c in m.certs],
                "opted_out": m.opted_out,
                "quiet_hours": list(m.quiet_hours),
                "asks_this_week": m.asks_this_week,
                "weekly_ask_limit": d.weekly_ask_limit,
                "overall": {"yes": yes, "no": no,
                            "probability": round(response_probability(yes, no), 3)},
                "by_window": stats,
                "messages": mine,
                "poll_count": sum(1 for x in mine
                                  if x["direction"] == "out" and x["purpose"] == "poll"),
                "asked_count": sum(1 for x in mine
                                   if x["direction"] == "out" and x["purpose"] == "ask"),
                "held_count": sum(1 for x in mine if x["held"]),
            })
        from turnout.agentcore.memory import status as memory_status

        return {
            "department": {"name": d.name, "short_name": d.short_name,
                           "weekly_ask_limit": d.weekly_ask_limit,
                           "chief_interrupt_budget": DAILY_INTERRUPT_BUDGET},
            # Counted, not claimed. Every answer a member gives is written to this department's own
            # AgentCore Memory, and this says how many actually landed there.
            "memory": memory_status("millbrook"),
            "prior": {"mean": 0.32, "strength": 10,
                      "source": "Predictive Dispatch of Volunteer First Responders, 2023"},
            "members": out,
        }

    def trace(self, since: int = 0) -> dict:
        return {"events": self.rt.trace[since:], "next": len(self.rt.trace)}

    def network(self) -> dict:
        r = self.rt
        depts = [r.store.get_department(x) for x in ("millbrook", "riverton", "cedar")]
        return {
            "departments": [{"id": d.id, "name": d.name, "short_name": d.short_name,
                             "coordinates": list(d.coordinates), "peers": d.peers,
                             "auto_approve": d.auto_approve.model_dump()} for d in depts],
            "edges": [{"from": "millbrook", "to": p,
                       "balance_hours": r.store.ledger_balance("millbrook", p)}
                      for p in ("riverton", "cedar")],
            "exchanges": [e for e in r.trace if e["kind"].startswith("a2a")],
        }


class _LazyService:
    """One DemoService for the process, built on first use.

    Building it loads a year of synthetic calls for three departments, so doing it at import time
    would slow every startup, including the tests that never touch the API.
    """

    _instance: DemoService | None = None

    def _get(self) -> DemoService:
        if _LazyService._instance is None:
            _LazyService._instance = DemoService()
        return _LazyService._instance

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get(), name)


service = _LazyService()
