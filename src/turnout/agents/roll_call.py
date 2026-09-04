"""Roll Call: the daily poll and the inbound reply handler.

Deterministic where it can be (the rule parser), model-backed only for replies the rules cannot read.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from turnout import runtime
from turnout.messaging import fmt_day, fmt_hour, render
from turnout.models import AvailabilityRecord, Message, ParsedReply
from turnout.parsing import parse_reply
from turnout.tools.chief import apply_chief_reply
from turnout.tools.roster import learn_response

POLL_START_HOUR, POLL_END_HOUR = 8, 17


def send_daily_polls(for_day: datetime | None = None) -> int:
    """Poll every active member about the next day's daytime window. One text each."""
    r = runtime.get()
    d = r.store.get_department(r.dept_id)
    day = (for_day or (r.clock.now() + timedelta(days=1))).replace(hour=0, minute=0, second=0, microsecond=0)
    start, end = day.replace(hour=POLL_START_HOUR), day.replace(hour=POLL_END_HOUR)
    n = 0
    for m in r.store.list_members(d.id):
        if m.opted_out:
            continue
        body = render("poll", dept=d.short_name, day=fmt_day(start), start=fmt_hour(start), end=fmt_hour(end))
        r.sms.send(d.id, m.phone, body, "poll", member_id=m.id)
        # a pending record so we know which window the reply refers to
        r.store.put_availability(AvailabilityRecord(dept_id=d.id, member_id=m.id, window_start=start, window_end=end,
                                                    status="unknown", source="poll", recorded_at=r.clock.now()))
        n += 1
    r.emit("polls_sent", count=n, window=f"{start:%a %H:%M}-{end:%H:%M}")
    return n


def _last_outbound(r, dept_id: str, phone: str) -> Message | None:
    msgs = [m for m in r.store.list_messages(dept_id, phone) if m.direction == "out"
            and m.purpose in ("poll", "ask", "swap", "clarify", "cert")]
    return msgs[-1] if msgs else None


MODEL_TRUST = 0.75
"""How sure the model must be before its reading of a free-text reply counts as
availability. Below this the member is asked again and nothing is recorded, because an
availability that is not really there is worse than an extra text."""


def _window_for(r, dept_id: str, member_id: str, purpose: str) -> tuple[datetime, datetime] | None:
    """The window the member's reply refers to: the pending poll window, or the gap they were asked about."""
    now = r.clock.now()
    if purpose in ("poll", "clarify"):
        recs = [a for a in r.store.list_availability(dept_id, now, now + timedelta(days=8))
                if a.member_id == member_id and a.source == "poll"]
        if recs:
            a = sorted(recs, key=lambda x: x.window_start)[0]
            return a.window_start, a.window_end
    if purpose == "ask":
        for g in r.store.list_gaps(dept_id, {"asking_members"}):
            if member_id in g.asked_member_ids:
                return g.window_start, g.window_end
        for g in r.store.list_gaps(dept_id):
            if member_id in g.asked_member_ids and g.window_end > now:
                return g.window_start, g.window_end
    return None


def handle_inbound(from_phone: str, text: str, at: datetime | None = None) -> dict:
    """Route an inbound SMS: member reply, chief decision, or keyword."""
    r = runtime.get()
    found = r.store.get_member_by_phone(from_phone)
    if found is None:
        for d in r.store.list_departments():
            if from_phone in (d.chief_phone, d.deputy_phone):
                r.dept_id = d.id
                return _handle_chief(text)
        return {"handled": False, "reason": "unknown number"}
    d, m = found
    r.dept_id = d.id
    parsed = parse_reply(text)
    last = _last_outbound(r, d.id, m.phone)
    purpose = last.purpose if last else "poll"
    window = _window_for(r, d.id, m.id, purpose)

    if parsed.intent == "unknown" and window:
        desc = f"{window[0]:%A} {window[0]:%H:%M}-{window[1]:%H:%M}"
        try:
            parsed = roll_call_llm(text, desc, purpose)
            r.emit("roll_call_llm", member_id=m.id, text=text, intent=parsed.intent,
                   confidence=parsed.confidence)
            # A model reading of a sentence like "depends on the kids, probably not" must clear a
            # bar before it becomes availability. Recording someone as available when they did not
            # clearly say yes is the dangerous direction: the board looks covered and nobody comes.
            # Below the bar, ask plainly and record nothing.
            if parsed.intent in ("yes", "partial") and parsed.confidence < MODEL_TRUST:
                r.emit("roll_call_low_confidence", member_id=m.id, text=text,
                       intent=parsed.intent, confidence=parsed.confidence,
                       action="asked again, nothing recorded")
                r.sms.send(d.id, m.phone,
                           render("clarify_plain", dept=d.short_name, day=fmt_day(window[0]),
                                  start=fmt_hour(window[0]), end=fmt_hour(window[1])),
                           "clarify", member_id=m.id)
                return {"handled": True, "intent": "unclear", "confidence": parsed.confidence}
        except Exception as e:
            r.emit("roll_call_llm_error", member_id=m.id, error=str(e)[:200])

    if parsed.intent == "stop":
        m.opted_out = True
        r.store.put_member(m)
        r.sms.send(d.id, m.phone, render("stop", dept=d.short_name), "system", member_id=m.id)
        return {"handled": True, "intent": "stop"}
    if parsed.intent == "start":
        m.opted_out = False
        r.store.put_member(m)
        r.sms.send(d.id, m.phone, render("start", dept=d.short_name), "system", member_id=m.id)
        return {"handled": True, "intent": "start"}
    if parsed.intent == "help":
        r.sms.send(d.id, m.phone, render("help", dept=d.short_name), "system", member_id=m.id)
        return {"handled": True, "intent": "help"}
    if parsed.intent == "limits":
        r.sms.send(d.id, m.phone, render("limits", dept=d.short_name, qh_start=f"{m.quiet_hours[0]}:00",
                                         qh_end=f"{m.quiet_hours[1]}:00", asks=m.asks_this_week,
                                         limit=d.weekly_ask_limit), "system", member_id=m.id)
        return {"handled": True, "intent": "limits"}
    if window is None:
        r.sms.send(d.id, m.phone, render("help", dept=d.short_name), "system", member_id=m.id)
        return {"handled": True, "intent": parsed.intent, "note": "no pending window"}

    start, end = window
    src = "ask" if purpose == "ask" else "poll"
    if parsed.intent == "yes":
        _record(r, d.id, m.id, start, end, "available", src, text)
        echo = render("ask_echo_yes", dept=d.short_name, day=fmt_day(start), start=fmt_hour(start), end=fmt_hour(end)) \
            if src == "ask" else render("poll_echo_yes", dept=d.short_name, day=fmt_day(start))
        if src == "ask":
            learn_response(m.id, start, True)
    elif parsed.intent == "no":
        _record(r, d.id, m.id, start, end, "unavailable", src, text)
        echo = render("ask_echo_no", dept=d.short_name) if src == "ask" else \
            render("poll_echo_no", dept=d.short_name, day=fmt_day(start))
        if src == "ask":
            learn_response(m.id, start, False)
    elif parsed.intent == "partial":
        ps = start.replace(hour=parsed.window_start_hour) if parsed.window_start_hour is not None else start
        pe = start.replace(hour=parsed.window_end_hour) if parsed.window_end_hour is not None else end
        if pe <= ps:
            r.sms.send(d.id, m.phone, render("clarify", dept=d.short_name, day=fmt_day(start)),
                       "clarify", member_id=m.id)
            return {"handled": True, "intent": "clarify"}
        _record(r, d.id, m.id, ps, pe, "partial", src, text)
        # the original poll window is resolved too, as unavailable outside the partial span
        until = fmt_hour(pe) if parsed.window_end_hour else f"from {fmt_hour(ps)}"
        echo = render("poll_echo_partial", dept=d.short_name, day=fmt_day(start), until=until)
        if src == "ask":
            learn_response(m.id, start, True)
    else:
        r.sms.send(d.id, m.phone, render("clarify", dept=d.short_name, day=fmt_day(start)), "clarify", member_id=m.id)
        return {"handled": True, "intent": "clarify"}
    r.sms.send(d.id, m.phone, echo, "ack", member_id=m.id)
    return {"handled": True, "intent": parsed.intent, "window": [start.isoformat(), end.isoformat()]}


def _record(r, dept_id: str, member_id: str, start: datetime, end: datetime, status: str, source: str,
            note: str) -> None:
    # drop the pending "unknown" poll record for this member, then store the answer
    lst = r.store.availability.get(dept_id, []) if hasattr(r.store, "availability") else []
    lst[:] = [a for a in lst if not (a.member_id == member_id and a.status == "unknown")]
    r.store.put_availability(AvailabilityRecord(dept_id=dept_id, member_id=member_id, window_start=start,
                                                window_end=end, status=status, source=source, note=note,
                                                recorded_at=r.clock.now()))
    r.emit("availability", member_id=member_id, window_start=start.isoformat(), window_end=end.isoformat(),
           status=status, source=source)


def _handle_chief(text: str) -> dict:
    parsed = parse_reply(text)
    if parsed.intent == "decision" and parsed.decision_choice:
        return apply_chief_reply(parsed.decision_choice)
    if parsed.intent in ("status", "gaps"):
        from turnout.tools.chief import send_status

        return send_status()
    return {"handled": False, "reason": "chief text not understood", "text": text}


def roll_call_llm(text: str, window_desc: str, purpose: str) -> ParsedReply:
    from turnout.agents.department import roll_call_parse

    return roll_call_parse(text, window_desc, purpose)
