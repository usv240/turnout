"""Run the demo week locally.

python -m turnout.sim.runner --scenario data/scenarios/demo_week.json --out data/runs/demo_week

Steps (all with real agents on Bedrock, simulated clock and SMS):
  Wed 06:30  Roll Call polls Millbrook for Thursday.
  Wed 07:30  Coverage pass 1: Watch finds the critical gap, Closer asks two members (one held).
  Wed 08:45  Coverage pass 2: declines in, Neighbor asks Riverton and Cedar Hollow over A2A, Chief Gate texts.
  Wed 08:47  Chief replies 1. Riverton auto-approves. Ledger updated. Members told.
  Wed 09:15  Coverage pass 3: afternoon gap closed by a member's yes.
  Thu 11:52  Incident. Scribe drafts NERIS from the voice note.
  Nightly    Cert Clock proposes a refresher for the expiring EMT card.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from turnout import runtime
from turnout.agents.department import cert_clock_agent, run_coverage_pass, scribe_agent
from turnout.agents.roll_call import handle_inbound, send_daily_polls
from turnout.clock import Clock
from turnout.models import AvailabilityRecord, Call, Department, Incident, Member, WeatherAlert
from turnout.store import MemoryStore
from turnout.tools.sms import flush_held


def load_scenario(path: str) -> tuple[MemoryStore, dict]:
    blob = json.loads(Path(path).read_text(encoding="utf-8"))
    st = MemoryStore()
    for d in blob["departments"]:
        st.put_department(Department.model_validate(d))
    for m in blob["members"]:
        st.put_member(Member.model_validate(m))
    st.put_calls([Call.model_validate(c) for c in blob["calls"]])
    for a in blob.get("availability", []):
        st.put_availability(AvailabilityRecord.model_validate(a))
    return st, blob["scenario"]


def setup(scenario_path: str, dept_id: str = "millbrook") -> tuple[runtime.Runtime, dict]:
    st, sc = load_scenario(scenario_path)
    clock = Clock(datetime.fromisoformat(sc["clock_start"]))
    rt = runtime.local_runtime(dept_id, clock=clock, store=st)
    # In the deployed container the peer departments run as their own A2A servers, so the demo
    # negotiates over real HTTP. Locally they run in process, so one command is enough to try it.
    if os.environ.get("TURNOUT_USE_A2A", "").lower() in ("1", "true", "yes"):
        rt.use_a2a = True
    for a in sc.get("weather_alerts", []):
        rt.weather.add(a["zone"], WeatherAlert(event=a["event"], start=datetime.fromisoformat(a["start"]),
                                               end=datetime.fromisoformat(a["end"]), multiplier=a["multiplier"]))
    # scripted phones
    members = {m.id: m for m in st.list_members("millbrook")}
    for mid, reply in sc["millbrook_poll_replies"].items():
        if reply is not None:
            rt.sms.script(members[mid].phone, "poll", reply, delay_min=8 + (hash(mid) % 40))
    for mid, reply in sc["millbrook_ask_replies"].items():
        rt.sms.script(members[mid].phone, "ask", reply, delay_min=12)
    rt.sms.script(st.get_department("millbrook").chief_phone, "decision", sc["chief_reply"], delay_min=2)
    rt.sms.inbound_handler = lambda phone, body, at: handle_inbound(phone, body, at)
    runtime.configure(rt)
    return rt, sc


def tick_until(rt: runtime.Runtime, until: datetime, step_min: int = 15) -> None:
    """Advance the simulated clock, delivering held sends and scripted replies as their times pass."""
    while rt.clock.now() < until:
        rt.clock.advance(minutes=min(step_min, int((until - rt.clock.now()).total_seconds() // 60) or step_min))
        flush_held(rt)
        rt.sms.deliver_due()
        rt.dept_id = "millbrook"


def run(scenario_path: str, out_dir: str, skip_llm_extras: bool = False) -> dict:
    rt, sc = setup(scenario_path)
    log: list[str] = []

    def say(s: str) -> None:
        log.append(s)
        # Windows consoles are cp1252; model prose can carry characters it cannot encode
        print(s.encode("ascii", "replace").decode("ascii"))

    t0 = rt.clock.now()
    say(f"== {t0:%a %Y-%m-%d %H:%M}  Roll Call: polling Millbrook for Thursday")
    rt.dept_id = "millbrook"
    n = send_daily_polls()
    say(f"   {n} polls sent")

    tick_until(rt, t0.replace(hour=7, minute=30))
    say(f"== {rt.clock.now():%a %H:%M}  Coverage pass 1")
    s1 = run_coverage_pass("morning")
    say("   order: " + " -> ".join(s1["order"]))

    tick_until(rt, t0.replace(hour=8, minute=45))
    say(f"== {rt.clock.now():%a %H:%M}  Coverage pass 2")
    s2 = run_coverage_pass("after member replies")
    say("   order: " + " -> ".join(s2["order"]))

    tick_until(rt, t0.replace(hour=8, minute=50))  # chief's scripted reply lands at +2 min
    tick_until(rt, t0.replace(hour=9, minute=15))
    say(f"== {rt.clock.now():%a %H:%M}  Coverage pass 3")
    s3 = run_coverage_pass("after chief decision")
    say("   order: " + " -> ".join(s3["order"]))

    tick_until(rt, t0.replace(hour=10, minute=45))
    say(f"== {rt.clock.now():%a %H:%M}  Coverage pass 4")
    s4 = run_coverage_pass("late morning")
    say("   order: " + " -> ".join(s4["order"]))

    if not skip_llm_extras:
        # Thursday incident and Scribe
        inc_at = datetime.fromisoformat(sc["incident"]["at"])
        tick_until(rt, inc_at + timedelta(minutes=70), step_min=120)
        inc = Incident(id="inc-0001", dept_id="millbrook", at=inc_at, transcript=sc["incident"]["voice_note"])
        rt.store.put_incident(inc)
        say(f"== {rt.clock.now():%a %H:%M}  Scribe: drafting NERIS from the voice note")
        res = scribe_agent()(f"Draft the NERIS report for incident inc-0001. Dispatch was {inc_at:%H:%M}, "
                             f"district {sc['incident']['district']}, Riverton covered under mutual aid.")
        say("   " + str(res).strip()[:300].replace("\n", " "))

        # Nightly Cert Clock
        say(f"== {rt.clock.now():%a %H:%M}  Cert Clock")
        res = cert_clock_agent()("Nightly certification check.")
        say("   " + str(res).strip()[:300].replace("\n", " "))

    # Summary
    say("")
    say("== Gaps (Millbrook)")
    for g in rt.store.list_gaps("millbrook"):
        if g.level.value in ("elevated", "high", "critical"):
            say(f"   {g.window_start:%a %H:%M}-{g.window_end:%H:%M} {g.level.value.upper():8} {g.risk_score:.2f} "
                f"{g.status:16} {g.covered_by or ''}  | {g.explanation}")
    say("== Ledger")
    for p in ("riverton", "cedar"):
        say(f"   millbrook vs {p}: {rt.store.ledger_balance('millbrook', p):+.1f} h")
    chief = rt.store.get_department("millbrook").chief_phone
    say("== Chief's phone")
    for m in rt.store.list_messages("millbrook", chief):
        say(f"   [{m.at:%a %H:%M}] {'<-' if m.direction == 'out' else '->'} {m.body!r}")
    outbound = [m for m in rt.store.list_messages("millbrook") if m.direction == "out" and m.member_id]
    held = sum(1 for m in outbound if m.held_for_quiet_hours)
    say(f"== Member texts sent: {len(outbound)}; held for quiet hours: {held}")

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rt.store.save(str(out / "state.json"))
    (out / "trace.json").write_text(json.dumps(rt.trace, indent=1, default=str), encoding="utf-8")
    (out / "log.txt").write_text("\n".join(log), encoding="utf-8")
    return {"gaps": [g.model_dump(mode="json") for g in rt.store.list_gaps("millbrook")], "trace_events": len(rt.trace)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="data/scenarios/demo_week.json")
    ap.add_argument("--out", default="data/runs/demo_week")
    ap.add_argument("--quick", action="store_true", help="skip Scribe and Cert Clock")
    a = ap.parse_args()
    run(a.scenario, a.out, skip_llm_extras=a.quick)


if __name__ == "__main__":
    main()
