"""Serve one department's Coverage agent over A2A.

    python -m turnout.a2a.server --dept riverton --port 9002

Each department is its own process, with its own store, its own memory, and its own AgentCard. A
neighbour can ask it to cover a window and can confirm an offer. It cannot read the roster.
"""

from __future__ import annotations

import argparse
from datetime import datetime

from turnout import runtime
from turnout.clock import Clock
from turnout.models import WeatherAlert

SKILLS = [
    ("request_coverage", "Request coverage",
     "Ask this department whether it can cover a time window and district for a neighbour."),
    ("confirm_coverage", "Confirm coverage",
     "Confirm a coverage offer this department previously made."),
]


def build_server(dept_id: str, port: int, scenario: str, host: str = "127.0.0.1"):
    """Build the A2A server for one department and configure its runtime."""
    from a2a.types import AgentSkill
    from strands.multiagent.a2a import A2AServer

    from turnout.agents.department import coverage_peer_agent
    from turnout.sim.runner import load_scenario

    store, sc = load_scenario(scenario)
    rt = runtime.local_runtime(dept_id, clock=Clock(datetime.fromisoformat(sc["clock_start"])), store=store)
    for a in sc.get("weather_alerts", []):
        rt.weather.add(a["zone"], WeatherAlert(event=a["event"], start=datetime.fromisoformat(a["start"]),
                                               end=datetime.fromisoformat(a["end"]), multiplier=a["multiplier"]))
    runtime.configure(rt)
    d = store.get_department(dept_id)
    skills = [AgentSkill(id=i, name=n, description=desc, tags=["mutual-aid", "fire", "ems"])
              for i, n, desc in SKILLS]
    server = A2AServer(agent=coverage_peer_agent(rt), host=host, port=port, version="1.0.0",
                       skills=skills, http_url=f"http://{host}:{port}")
    return server, d, rt


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dept", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--scenario", default="data/scenarios/demo_week.json")
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    server, d, _ = build_server(a.dept, a.port, a.scenario, a.host)
    print(f"{d.name} coverage agent listening on http://{a.host}:{a.port}")
    server.serve()


if __name__ == "__main__":
    main()
