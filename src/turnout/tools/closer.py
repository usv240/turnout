"""Closer's tools: rank candidates, record asks, check replies.

Each tool owns the gap's state transition, so the workflow cannot stall because a prompt forgot a step.
The agent decides who to ask and what to say; the tools decide what the gap's status becomes.
"""

from __future__ import annotations

from datetime import timedelta

from strands import tool

from turnout.engine.risk import response_probability, window_type
from turnout.messaging import fmt_day, fmt_hour, role_word
from turnout.models import ResponseStats
from turnout.tools.common import dept, in_quiet_hours, now, rt
from turnout.tools.coverage import _gap_summary, compute_gaps

MAX_ASKS_PER_ROUND = 2


@tool
def rank_candidates(gap_id: str, limit: int = 4) -> list[dict]:
    """Members who could close a gap, ranked by predicted probability of saying yes for that window.

    Excludes members who already answered about that day, opted-out members, members at their weekly ask
    limit, and members who cannot fill any missing role. Flags members currently in quiet hours, whose ask
    will be held until quiet hours end. If the gap's missing roles changed since the last round (someone
    said yes and the gap is now short a different role), previously asked members are eligible again.

    Args:
        gap_id: the gap id.
        limit: how many to return.
    """
    r = rt()
    d = dept()
    g = r.store.get_gap(d.id, gap_id)
    missing = set(g.inputs.missing_roles) or set(d.min_crew.fire)
    new_round = bool(g.asked_for_roles) and set(g.asked_for_roles) != missing
    day_start = g.window_start.replace(hour=0, minute=0, second=0, microsecond=0)
    recs = r.store.list_availability(d.id, day_start, day_start + timedelta(days=1))
    answered = {a.member_id for a in recs if a.status in ("available", "partial", "unavailable")}
    wt = window_type(g.window_start)
    out = []
    for m in r.store.list_members(d.id):
        if m.opted_out or m.id in answered:
            continue
        if m.id in g.asked_member_ids and not new_round:
            continue
        if not (set(m.roles) & missing):
            continue
        if m.asks_this_week >= d.weekly_ask_limit:
            continue
        s = m.response_stats.get(wt, ResponseStats())
        out.append({"member_id": m.id, "name": m.name, "roles": [x.value for x in m.roles],
                    "probability": round(response_probability(s.yes, s.no), 3),
                    "in_quiet_hours": in_quiet_hours(now().hour, m.quiet_hours),
                    "fills": sorted(x.value for x in (set(m.roles) & missing))})
    out.sort(key=lambda x: (-x["probability"], x["member_id"]))
    return out[:limit]


@tool
def send_ask(gap_id: str, member_id: str) -> dict:
    """Text one member asking them to cover a specific gap, and record the ask.

    Builds the message from the gap itself, so the day, the hours and the role are always right. Picks the
    role from the gap's missing roles that this member can fill. Honors quiet hours, the weekly ask limit,
    and opt-outs. Call this once per member; it also sets the gap's status to asking_members.

    Args:
        gap_id: the gap id, exactly as list_gaps returned it.
        member_id: the member to ask.
    """
    r = rt()
    d = dept()
    known = {g.id for g in r.store.list_gaps(d.id)}
    if gap_id not in known:
        return {"sent": False, "error": "no gap with that id. Call list_gaps and use an id exactly as shown.",
                "valid_gap_ids": sorted(known)}
    g = r.store.get_gap(d.id, gap_id)
    m = r.store.get_member(d.id, member_id)
    missing = set(g.inputs.missing_roles) or set(d.min_crew.fire)
    fills = set(m.roles) & missing
    if not fills:
        return {"sent": False, "error": f"{m.name} cannot fill any of {sorted(x.value for x in missing)}"}
    role = sorted(fills)[0]
    from turnout.tools.sms import send_member_sms_impl

    res = send_member_sms_impl(member_id, "ask", {
        "day": fmt_day(g.window_start), "start": fmt_hour(g.window_start), "end": fmt_hour(g.window_end),
        "role": role_word(role.value)}, "ask")
    if res.get("sent") or res.get("held_until"):
        _mark(g, [member_id])
    return {**res, "gap_id": gap_id, "role_asked": role_word(role.value)}


def _mark(g, member_ids: list[str], wait_minutes: int = 90) -> None:
    r = rt()
    missing = list(g.inputs.missing_roles)
    if set(g.asked_for_roles) != set(missing):
        g.asked_member_ids = []
    g.asked_member_ids = sorted(set(g.asked_member_ids) | set(member_ids))
    g.asked_for_roles = missing
    g.asked_at = now()
    g.next_check = now() + timedelta(minutes=wait_minutes)
    g.status = "asking_members"
    r.store.put_gap(g)
    r.emit("gap_status", gap_id=g.id, status="asking_members", asked=member_ids,
           for_roles=[x.value for x in missing])


@tool
def mark_asked(gap_id: str, member_ids: list[str], wait_minutes: int = 90) -> dict:
    """Record that targeted asks went out for a gap and set its status to asking_members.

    Args:
        gap_id: the gap id.
        member_ids: members who were asked.
        wait_minutes: how long to wait for replies before moving on. Default 90.
    """
    r = rt()
    g = r.store.get_gap(r.dept_id, gap_id)
    _mark(g, member_ids, wait_minutes)
    return _gap_summary(g)


@tool
def check_asks(gap_id: str) -> dict:
    """Check on a gap we asked members about, and move it forward.

    Recomputes coverage first, then sets the gap's status itself and tells you what to do next:
      covered           the gap closed, nothing more to do
      ask_again         someone said yes but the gap is now short a different role; rank candidates again
      still_waiting     replies are still coming, leave it
      members_declined  our own members cannot close it; Neighbor takes it from here

    Args:
        gap_id: the gap id.
    """
    r = rt()
    d = dept()
    known = {g.id for g in r.store.list_gaps(d.id)}
    if gap_id not in known:
        return {"gap_id": gap_id, "next_action": "error",
                "detail": "no gap with that id. Call list_gaps and use an id exactly as it appears there.",
                "valid_gap_ids": sorted(known)}
    compute_gaps()
    g = r.store.get_gap(d.id, gap_id)
    if g.status == "covered":
        return {"gap_id": gap_id, "next_action": "covered", "detail": g.resolution}

    day_start = g.window_start.replace(hour=0, minute=0, second=0, microsecond=0)
    recs = r.store.list_availability(d.id, day_start, day_start + timedelta(days=1))
    replies = {a.member_id: a.status for a in recs if a.member_id in g.asked_member_ids and a.source == "ask"}
    pending = [m for m in g.asked_member_ids if m not in replies]
    missing_now = set(g.inputs.missing_roles)
    roles_changed = bool(g.asked_for_roles) and set(g.asked_for_roles) != missing_now
    expired = bool(g.next_check and now() >= g.next_check)

    # Progress was made, so a fresh round is allowed, but only if anyone is left to ask.
    if roles_changed and not pending and rank_candidates(gap_id, limit=1):
        r.emit("gap_status", gap_id=gap_id, status="asking_members", note="missing role changed, ask again")
        return {"gap_id": gap_id, "next_action": "ask_again", "replies": replies,
                "missing_roles": sorted(x.value for x in missing_now)}
    if pending and not expired:
        return {"gap_id": gap_id, "next_action": "still_waiting", "pending": pending, "replies": replies,
                "until": g.next_check.isoformat() if g.next_check else None}

    g.status = "members_declined"
    g.resolution = "our own members cannot cover this window"
    r.store.put_gap(g)
    r.emit("gap_status", gap_id=gap_id, status="members_declined", replies=replies, pending=pending)
    return {"gap_id": gap_id, "next_action": "members_declined", "replies": replies, "pending": pending,
            "missing_roles": sorted(x.value for x in missing_now)}
