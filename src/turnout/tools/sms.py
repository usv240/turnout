"""SMS tools. Templates only. Quiet hours are enforced here (hold), ask limits and opt-outs in the hook."""

from __future__ import annotations

import json

from strands import tool

from turnout.messaging import CHIEF_MAX, render, templates
from turnout.tools.common import dept, in_quiet_hours, now, quiet_hours_end, rt


@tool
def send_member_sms(member_id: str, template: str, slots_json: str = "{}", purpose: str = "") -> dict:
    """Send a templated text to a member. If the member is in quiet hours the text is held and sent
    when quiet hours end, with a note saying so. Never sends free text.

    Args:
        member_id: the member id.
        template: template key from messages.yaml, for example poll, swap, covered, cert, clarify.
        slots_json: JSON object of template slots. The dept slot is filled automatically.
        purpose: poll, swap, covered, cert, clarify, ack, system. Defaults to the template key.
    """
    return send_member_sms_impl(member_id, template, json.loads(slots_json) if slots_json else {}, purpose)


def send_member_sms_impl(member_id: str, template: str, slots: dict, purpose: str = "") -> dict:
    r = rt()
    d = dept()
    m = r.store.get_member(d.id, member_id)
    slots = dict(slots)
    slots.setdefault("dept", d.short_name)
    purpose = purpose or template
    body = render(template, **slots)
    t = now()
    held = in_quiet_hours(t.hour, m.quiet_hours) and purpose in ("ask", "swap", "cert", "clarify")
    if held:
        due = quiet_hours_end(t, m.quiet_hours)
        body = templates()["held_prefix"] + body
        # the channel sends at `due`; in simulation the clock will pass it, on AWS a scheduler does
        r.sms.pending_outbound = getattr(r.sms, "pending_outbound", [])
        r.sms.pending_outbound.append({"due": due, "dept_id": d.id, "to": m.phone, "body": body,
                                       "purpose": purpose, "member_id": m.id})
        r.emit("sms_held", member_id=m.id, until=due.isoformat(), purpose=purpose)
        if purpose == "ask":
            m.asks_this_week += 1
            r.store.put_member(m)
        return {"sent": False, "held_until": due.isoformat(), "member_id": m.id, "body": body}
    r.sms.send(d.id, m.phone, body, purpose, member_id=m.id)
    if purpose == "ask":
        m.asks_this_week += 1
        r.store.put_member(m)
    return {"sent": True, "member_id": m.id, "body": body}


@tool
def send_chief_sms(template: str, slots_json: str = "{}", to_deputy: bool = False) -> dict:
    """Send a templated text to the chief (or deputy).

    Args:
        template: template key, for example decision, decision_no_offer, approved, left_open, status, weekly,
                  escalation, undone.
        slots_json: JSON object of template slots. The dept slot is filled automatically.
        to_deputy: send to the deputy chief instead.
    """
    r = rt()
    d = dept()
    slots = json.loads(slots_json) if slots_json else {}
    slots.setdefault("dept", d.short_name)
    body = render(template, **slots)
    to = d.deputy_phone if to_deputy and d.deputy_phone else d.chief_phone
    r.sms.send(d.id, to, body, template)
    return {"sent": True, "to": "deputy" if to_deputy else "chief", "body": body}


@tool
def send_chief_options(lines: list[str]) -> dict:
    """Send the chief a short list of alternatives, one per line, under 300 characters total.

    Args:
        lines: option lines such as "2a Cedar Hollow, 14 min delay" and a final instruction line.
    """
    r = rt()
    d = dept()
    body = f"{d.short_name}: " + "\n".join(lines)
    if len(body) > CHIEF_MAX:
        body = body[: CHIEF_MAX - 1]
    r.sms.send(d.id, d.chief_phone, body, "options")
    return {"sent": True, "body": body}


def flush_held(r) -> int:
    """Send held messages whose quiet hours have ended. Called by the scheduler and the simulation."""
    pend = getattr(r.sms, "pending_outbound", [])
    t = r.clock.now()
    due = [p for p in pend if p["due"] <= t]
    r.sms.pending_outbound = [p for p in pend if p["due"] > t]
    for p in sorted(due, key=lambda x: x["due"]):
        r.sms.send(p["dept_id"], p["to"], p["body"], p["purpose"], member_id=p["member_id"], held=True)
    return len(due)
