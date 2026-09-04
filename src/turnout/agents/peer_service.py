"""The receiving side of mutual aid. A department evaluates a neighbor's request against its own coverage.

This is deterministic and is exposed both as a tool for the Coverage peer agent (over A2A) and directly
for in-process peers in the local demo. The same code answers in both cases.
"""

from __future__ import annotations

import json
import math
from datetime import timedelta

from strands import tool

from turnout import runtime
from turnout.engine.feasibility import is_feasible
from turnout.engine.risk import RateModel, response_probability, score_window, window_type
from turnout.models import CoverageConfirm, CoverageOffer, CoverageRequest, ResponseStats, Role
from turnout.tools.ledger import record_ledger

TURNOUT_MIN = 3
SPEED_KMH = 56.0


def travel_minutes(a: tuple[float, float], b: tuple[float, float]) -> int:
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    km = 2 * 6371 * math.asin(math.sqrt(h))
    return int(round(km / SPEED_KMH * 60)) + TURNOUT_MIN


def evaluate_request(req: CoverageRequest) -> CoverageOffer:
    """Decide whether this department can cover a neighbor's window."""
    r = runtime.get()
    d = r.store.get_department(r.dept_id)
    members = r.store.list_members(d.id)
    recs = r.store.list_availability(d.id, req.window_start, req.window_end)
    calls = r.store.list_calls(d.id, r.clock.now() - timedelta(days=365))
    rate = RateModel.from_history(calls, r.clock.now())
    alerts = r.weather.active_alerts(d.weather_zone, req.window_start, req.window_end)

    avail = []
    for m in members:
        if m.opted_out:
            continue
        for a in recs:
            if a.member_id == m.id and a.status in ("available", "partial") \
                    and a.window_start <= req.window_start and a.window_end >= req.window_end:
                s = m.response_stats.get(window_type(req.window_start), ResponseStats())
                avail.append((m, response_probability(s.yes, s.no)))
                break
    own = score_window(req.window_start, req.window_end, [(set(m.roles), p) for m, p in avail], d.min_crew.fire,
                       rate, alerts)
    hours = (req.window_end - req.window_start).total_seconds() / 3600
    requester = r.store.get_department(req.from_dept) if req.from_dept in r.store.departments else None  # type: ignore[attr-defined]
    delay = travel_minutes(d.coordinates, requester.coordinates) if requester else 15

    # Can we spare a crew? We need our own minimum crew to remain feasible with the requested roles removed.
    role_sets = [set(m.roles) for m, _ in avail]
    spare_ok = False
    for i, rs in enumerate(role_sets):
        if set(req.roles_needed) & rs:
            rest = role_sets[:i] + role_sets[i + 1:]
            if is_feasible(rest, d.min_crew.fire) and is_feasible(role_sets, d.min_crew.fire):
                spare_ok = True
                break

    if own.level.value in ("high", "critical"):
        offer = CoverageOffer(request_id=req.request_id, from_dept=d.id, can_cover=False,
                              reason_if_declined=f"own {d.districts[0]} district at {own.level.value} risk in that window",
                              peer_current_risk=own.risk_score)
    elif not spare_ok:
        offer = CoverageOffer(request_id=req.request_id, from_dept=d.id, can_cover=False,
                              reason_if_declined="cannot spare a qualified crew in that window",
                              peer_current_risk=own.risk_score)
    else:
        offer = CoverageOffer(request_id=req.request_id, from_dept=d.id, can_cover=True,
                              estimated_delay_min=delay, roles=list(req.roles_needed),
                              conditions="single apparatus, our district remains covered",
                              ledger_delta_hours=round(hours, 1),
                              valid_until=r.clock.now() + timedelta(hours=9), peer_current_risk=own.risk_score,
                              auto_approved=d.auto_approve.enabled and delay <= d.auto_approve.max_delay_min)
    r.emit("a2a_offer", to=req.from_dept, request_id=req.request_id, can_cover=offer.can_cover,
           delay=offer.estimated_delay_min, reason=offer.reason_if_declined, own_risk=own.risk_score)
    return offer


def apply_confirm(conf: CoverageConfirm, req: CoverageRequest) -> dict:
    """The requester confirmed. Apply auto-approval or queue for our chief. Record the ledger."""
    r = runtime.get()
    d = r.store.get_department(r.dept_id)
    hours = round((req.window_end - req.window_start).total_seconds() / 3600, 1)
    delay = travel_minutes(d.coordinates, r.store.get_department(req.from_dept).coordinates)
    balance_after = r.store.ledger_balance(d.id, req.from_dept) - hours
    auto = d.auto_approve.enabled and delay <= d.auto_approve.max_delay_min \
        and abs(balance_after) <= d.auto_approve.max_ledger_hours
    if auto:
        record_ledger(d.id, req.from_dept, "given", hours, req.request_id)
        r.emit("a2a_confirmed", frm=req.from_dept, request_id=req.request_id, auto_approved=True)
        return {"accepted": True, "auto_approved": True,
                "note": f"{d.short_name} auto-approved: delay {delay} min within {d.auto_approve.max_delay_min}, "
                        f"ledger within {d.auto_approve.max_ledger_hours} h"}
    # Not auto-approved: our chief must decide. Send the chief a decision text and hold.
    from turnout.messaging import render
    body = render("decision", dept=d.short_name, day=req.window_start.strftime("%a"),
                  start=req.window_start.strftime("%I%p").lstrip("0").lower(),
                  end=req.window_end.strftime("%I%p").lstrip("0").lower(), district=req.district,
                  level=f"NEIGHBOR REQUEST {req.risk_level.value.upper()}",
                  explanation=f"{req.from_dept} asks us to cover; {req.risk_explanation}",
                  recommendation=f"We can cover with {delay} min delay; they would owe us {hours} hrs")
    r.sms.send(d.id, d.chief_phone, body, "decision")
    r.emit("a2a_pending_chief", frm=req.from_dept, request_id=req.request_id)
    return {"accepted": False, "pending_chief": True, "note": f"{d.short_name} chief must approve"}


@tool
def evaluate_coverage_request(request_json: str) -> str:
    """Evaluate a neighboring department's coverage request against our own coverage and risk.

    Args:
        request_json: JSON of a CoverageRequest.
    """
    req = CoverageRequest.model_validate_json(request_json)
    return evaluate_request(req).model_dump_json()


@tool
def apply_coverage_confirm(confirm_json: str) -> str:
    """Apply a requester's confirmation of our offer. Auto-approves within the chief's rule, else asks the chief.

    Args:
        confirm_json: JSON with keys confirm (CoverageConfirm) and request (CoverageRequest).
    """
    blob = json.loads(confirm_json)
    conf = CoverageConfirm.model_validate(blob["confirm"])
    req = CoverageRequest.model_validate(blob["request"])
    return json.dumps(apply_confirm(conf, req))
