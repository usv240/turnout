"""Cert Clock's tools."""

from __future__ import annotations

from datetime import timedelta

from strands import tool

from turnout.messaging import render
from turnout.tools.common import dept, now, rt


@tool
def find_expiring_certs(days: int = 90) -> list[dict]:
    """Members whose certifications expire within a number of days.

    Args:
        days: horizon, default 90.
    """
    r = rt()
    d = dept()
    out = []
    for m in r.store.list_members(d.id):
        for c in m.certs:
            if now() <= c.expires <= now() + timedelta(days=days):
                out.append({"member_id": m.id, "name": m.name, "cert": c.type,
                            "expires": c.expires.date().isoformat(), "days_left": (c.expires - now()).days})
    return sorted(out, key=lambda x: x["days_left"])


@tool
def propose_training(member_id: str, cert: str) -> dict:
    """Pick a refresher date for a member that fits their pattern (a Saturday at least two weeks out and at
    least three weeks before expiry) and text them the proposal.

    Args:
        member_id: the member id.
        cert: certification type, for example EMT-B.
    """
    r = rt()
    d = dept()
    m = r.store.get_member(d.id, member_id)
    exp = next((c.expires for c in m.certs if c.type == cert), None)
    if exp is None:
        return {"proposed": False, "reason": "no such certification"}
    t = now() + timedelta(days=14)
    while t.weekday() != 5:
        t += timedelta(days=1)
    latest = exp - timedelta(days=21)
    if t > latest:
        t = latest
    when = t.strftime("Sat %b %d, 9am at Station 1") if t.weekday() == 5 else t.strftime("%a %b %d, 9am at Station 1")
    body = render("cert", dept=d.short_name, cert=cert, expires=exp.strftime("%b %d"), when=when)
    r.sms.send(d.id, m.phone, body, "cert", member_id=m.id)
    r.emit("training_proposed", member_id=m.id, cert=cert, when=t.date().isoformat())
    return {"proposed": True, "member_id": m.id, "cert": cert, "date": t.date().isoformat(), "body": body}
