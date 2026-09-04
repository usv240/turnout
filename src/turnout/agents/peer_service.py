"""The receiving side of mutual aid: a department evaluating a neighbour's request.

This is deterministic. The same functions serve the in-process peer used by the local demo and the
A2A peer used across departments, so both paths give the same answer.

Peer tools are built as closures bound to one department's runtime (see make_peer_tools). Two
departments served from the same process therefore never read each other's store, which is what
makes the isolation between organizations real rather than assumed.
"""

from __future__ import annotations

import json
import math
from datetime import timedelta

from strands import tool

from turnout import runtime
from turnout.engine.feasibility import is_feasible
from turnout.engine.risk import RateModel, response_probability, score_window, window_type
from turnout.models import CoverageConfirm, CoverageOffer, CoverageRequest, ResponseStats
from turnout.tools.ledger import record_ledger

TURNOUT_MIN = 3
SPEED_KMH = 56.0


def travel_minutes(a: tuple[float, float], b: tuple[float, float]) -> int:
    """Great circle distance at rural road speed, plus turnout time."""
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    km = 2 * 6371 * math.asin(math.sqrt(h))
    return int(round(km / SPEED_KMH * 60)) + TURNOUT_MIN


def evaluate_request(req: CoverageRequest, rt=None) -> CoverageOffer:
    """Decide whether this department can cover a neighbour's window."""
    r = rt or runtime.get()
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
            if (a.member_id == m.id and a.status in ("available", "partial")
                    and a.window_start <= req.window_start and a.window_end >= req.window_end):
                s = m.response_stats.get(window_type(req.window_start), ResponseStats())
                avail.append((m, response_probability(s.yes, s.no)))
                break
    own = score_window(req.window_start, req.window_end, [(set(m.roles), p) for m, p in avail],
                       d.min_crew.fire, rate, alerts)
    hours = (req.window_end - req.window_start).total_seconds() / 3600
    try:
        delay = travel_minutes(d.coordinates, r.store.get_department(req.from_dept).coordinates)
    except KeyError:
        delay = 15

    # We can only spare a crew if our own minimum crew still stands without them.
    role_sets = [set(m.roles) for m, _ in avail]
    spare_ok = False
    if is_feasible(role_sets, d.min_crew.fire):
        for i, rs in enumerate(role_sets):
            if set(req.roles_needed) & rs and is_feasible(role_sets[:i] + role_sets[i + 1:], d.min_crew.fire):
                spare_ok = True
                break

    if own.level.value in ("high", "critical"):
        offer = CoverageOffer(
            request_id=req.request_id, from_dept=d.id, can_cover=False, peer_current_risk=own.risk_score,
            reason_if_declined=f"own {d.districts[0]} district at {own.level.value} risk in that window")
    elif not spare_ok:
        offer = CoverageOffer(
            request_id=req.request_id, from_dept=d.id, can_cover=False, peer_current_risk=own.risk_score,
            reason_if_declined="cannot spare a qualified crew in that window")
    else:
        offer = CoverageOffer(
            request_id=req.request_id, from_dept=d.id, can_cover=True, estimated_delay_min=delay,
            roles=list(req.roles_needed), conditions="single apparatus, our district remains covered",
            ledger_delta_hours=round(hours, 1), valid_until=r.clock.now() + timedelta(hours=9),
            peer_current_risk=own.risk_score,
            auto_approved=d.auto_approve.enabled and delay <= d.auto_approve.max_delay_min)
    r.emit("a2a_offer_sent", to=req.from_dept, request_id=req.request_id, can_cover=offer.can_cover,
           delay=offer.estimated_delay_min, reason=offer.reason_if_declined, own_risk=own.risk_score)
    return offer


def apply_confirm(conf: CoverageConfirm, req: CoverageRequest, rt=None) -> dict:
    """The requester confirmed our offer. Auto-approve inside the chief's rule, else ask our chief."""
    r = rt or runtime.get()
    d = r.store.get_department(r.dept_id)
    hours = round((req.window_end - req.window_start).total_seconds() / 3600, 1)
    try:
        delay = travel_minutes(d.coordinates, r.store.get_department(req.from_dept).coordinates)
    except KeyError:
        delay = 15
    balance_after = r.store.ledger_balance(d.id, req.from_dept) - hours
    auto = (d.auto_approve.enabled and delay <= d.auto_approve.max_delay_min
            and abs(balance_after) <= d.auto_approve.max_ledger_hours)
    if auto:
        record_ledger(d.id, req.from_dept, "given", hours, req.request_id, rt=r)
        r.emit("a2a_confirmed", frm=req.from_dept, request_id=req.request_id, auto_approved=True)
        return {"accepted": True, "auto_approved": True,
                "note": (f"{d.short_name} auto-approved: {delay} min delay is within "
                         f"{d.auto_approve.max_delay_min}, and the ledger stays within "
                         f"{d.auto_approve.max_ledger_hours} hours")}

    from turnout.messaging import fmt_day, fmt_hour, render

    body = render("decision", dept=d.short_name, day=fmt_day(req.window_start),
                  start=fmt_hour(req.window_start), end=fmt_hour(req.window_end), district=req.district,
                  level="NEIGHBOR ASK",
                  explanation=f"{req.from_dept.title()} is {req.risk_level.value}: {req.risk_explanation}",
                  recommendation=f"We can cover, {delay} min out. They would owe us {hours} hrs")
    r.sms.send(d.id, d.chief_phone, body, "decision")
    r.emit("a2a_pending_chief", frm=req.from_dept, request_id=req.request_id)
    return {"accepted": False, "pending_chief": True,
            "note": f"the chief at {d.short_name} must approve; delay or ledger is outside their rule"}


def make_peer_tools(rt):
    """Build this department's A2A tools, bound to its own runtime."""

    @tool
    def evaluate_coverage_request(request_json: str) -> str:
        """Evaluate a neighbouring department's coverage request against our own coverage and risk.

        Args:
            request_json: JSON of a CoverageRequest.
        """
        return evaluate_request(CoverageRequest.model_validate_json(request_json), rt=rt).model_dump_json()

    @tool
    def apply_coverage_confirm(confirm_json: str) -> str:
        """Apply a requester's confirmation of our offer. Auto-approves inside the chief's rule.

        Args:
            confirm_json: JSON with keys confirm (CoverageConfirm) and request (CoverageRequest).
        """
        blob = json.loads(confirm_json)
        return json.dumps(apply_confirm(CoverageConfirm.model_validate(blob["confirm"]),
                                        CoverageRequest.model_validate(blob["request"]), rt=rt))

    return [evaluate_coverage_request, apply_coverage_confirm]
