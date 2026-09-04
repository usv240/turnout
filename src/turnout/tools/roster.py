"""Roster and availability tools."""

from __future__ import annotations

from strands import tool

from turnout.engine.risk import response_probability, window_type
from turnout.models import AvailabilityRecord, ResponseStats
from turnout.tools.common import dept, now, parse_dt, rt


@tool
def get_department() -> dict:
    """Get this department's configuration: name, districts, minimum crew, peers, policies, chief phone."""
    d = dept()
    return d.model_dump(mode="json")


@tool
def list_members(include_opted_out: bool = False) -> list[dict]:
    """List members of this department with roles, quiet hours, asks used this week, and opt-out status.

    Args:
        include_opted_out: include members who replied STOP.
    """
    out = []
    for m in rt().store.list_members(rt().dept_id):
        if m.opted_out and not include_opted_out:
            continue
        out.append({"id": m.id, "name": m.name, "roles": [r.value for r in m.roles],
                    "quiet_hours": list(m.quiet_hours), "asks_this_week": m.asks_this_week,
                    "opted_out": m.opted_out})
    return out


@tool
def get_member_response_probability(member_id: str, window_start: str) -> dict:
    """Predicted probability this member responds in a window, from their own history (Beta posterior,
    prior mean 0.32 from the volunteer first responder literature).

    Args:
        member_id: the member id.
        window_start: ISO datetime of the window start; determines weekday/weekend and day/evening/night.
    """
    m = rt().store.get_member(rt().dept_id, member_id)
    wt = window_type(parse_dt(window_start))
    s = m.response_stats.get(wt, ResponseStats())
    return {"member_id": member_id, "window_type": wt, "yes": s.yes, "no": s.no,
            "probability": round(response_probability(s.yes, s.no), 3)}


@tool
def record_availability(member_id: str, window_start: str, window_end: str, status: str,
                        source: str = "poll", note: str = "") -> dict:
    """Record a member's availability for a window.

    Args:
        member_id: member id.
        window_start: ISO datetime.
        window_end: ISO datetime.
        status: available, unavailable, partial, or unknown.
        source: poll, ask, swap, manual, or import.
        note: the member's own words, if any.
    """
    r = rt()
    rec = AvailabilityRecord(dept_id=r.dept_id, member_id=member_id, window_start=parse_dt(window_start),
                             window_end=parse_dt(window_end), status=status, source=source, note=note,
                             recorded_at=now())
    r.store.put_availability(rec)
    r.emit("availability", member_id=member_id, window_start=window_start, window_end=window_end,
           status=status, source=source)
    return rec.model_dump(mode="json")


@tool
def list_availability(window_start: str, window_end: str) -> list[dict]:
    """Availability records overlapping a window.

    Args:
        window_start: ISO datetime.
        window_end: ISO datetime.
    """
    recs = rt().store.list_availability(rt().dept_id, parse_dt(window_start), parse_dt(window_end))
    return [a.model_dump(mode="json") for a in recs]


def learn_response(member_id: str, window_start, said_yes: bool) -> None:
    """Update a member's response stats from an ask reply (G13: learn from user behavior)."""
    r = rt()
    m = r.store.get_member(r.dept_id, member_id)
    wt = window_type(window_start)
    s = m.response_stats.get(wt, ResponseStats())
    if said_yes:
        s.yes += 1
    else:
        s.no += 1
    m.response_stats[wt] = s
    r.store.put_member(m)
