"""Chief Gate's tools: compose and send the interrupts, and apply the chief's reply.

The interrupt budget is enforced here, in code, not in the prompt. Gaps that need the same decision
(same day, same recommended peer) are combined into one text, and the number of interrupts per day is
capped. Everything that can wait goes into the weekly summary instead.
"""

from __future__ import annotations

from datetime import timedelta

from strands import tool

from turnout.messaging import fmt_day, fmt_hour, render
from turnout.models import Decision
from turnout.tools.common import dept, now, rt
from turnout.tools.peers import confirm_with_peer

DAILY_INTERRUPT_BUDGET = 3


def _slots(g) -> dict:
    d = dept()
    return {"dept": d.short_name, "day": fmt_day(g.window_start), "start": fmt_hour(g.window_start),
            "end": fmt_hour(g.window_end), "district": g.district, "level": g.level.value.upper(),
            "explanation": g.explanation[0].upper() + g.explanation[1:]}


def interrupts_today() -> int:
    r = rt()
    d = dept()
    today = now().date()
    return sum(1 for m in r.store.list_messages(d.id, d.chief_phone)
               if m.direction == "out" and m.purpose in ("decision", "escalation") and m.at.date() == today)


def _pending() -> list:
    r = rt()
    return sorted([g for g in r.store.list_gaps(r.dept_id, {"needs_chief", "no_options"})
                   if g.decision_sent_at is None and g.window_end > now()],
                  key=lambda g: (g.window_start, -g.risk_score))


@tool
def send_decisions(reason: str = "scheduled") -> dict:
    """Send the chief the interrupts that are due, batched.

    Gaps on the same day that the same neighbour would cover are combined into one text, so approving
    once covers all of them. Interrupts are capped per day; anything over the cap waits for the weekly
    summary. Returns what was sent and what was deferred.

    Args:
        reason: why this run is happening, for the trace. Optional.
    """
    r = rt()
    d = dept()
    pending = _pending()
    if not pending:
        return {"sent": 0, "note": "nothing needs the chief"}

    groups: dict[tuple, list] = {}
    for g in pending:
        peer = next((o.from_dept for o in g.offers if o.can_cover), None)
        groups.setdefault((g.window_start.date(), peer), []).append(g)

    budget = DAILY_INTERRUPT_BUDGET - interrupts_today()
    sent, deferred = [], []
    for (_day, _peer), gaps in sorted(groups.items(), key=lambda kv: -max(g.risk_score for g in kv[1])):
        if budget <= 0:
            deferred.extend(g.id for g in gaps)
            continue
        worst = max(gaps, key=lambda g: g.risk_score)
        slots = _slots(worst)
        if peer is None:
            body = render("decision_no_offer", **slots)
        elif len(gaps) == 1:
            offer = next(o for o in worst.offers if o.can_cover)
            rec = render("recommendation_offer", by=r.store.get_department(peer).short_name,
                         delay=offer.estimated_delay_min, dept=d.short_name.split()[0],
                         hours=offer.ledger_delta_hours)
            body = render("decision", recommendation=rec, **slots)
        else:
            hours = sum(next(o.ledger_delta_hours for o in g.offers if o.can_cover) for g in gaps)
            delay = max(next(o.estimated_delay_min for o in g.offers if o.can_cover) for g in gaps)
            rec = render("recommendation_offer", by=r.store.get_department(peer).short_name, delay=delay,
                         dept=d.short_name.split()[0], hours=round(hours, 1))
            windows = " and ".join(f"{fmt_hour(g.window_start)}-{fmt_hour(g.window_end)}" for g in gaps)
            body = render("decision_multi", dept=d.short_name, day=fmt_day(worst.window_start), n=len(gaps),
                          windows=windows, worst_explanation=slots["explanation"], recommendation=rec)
        r.sms.send(d.id, d.chief_phone, body, "decision")
        for g in gaps:
            g.decision_sent_at = now()
            r.store.put_gap(g)
            r.store.put_decision(Decision(dept_id=d.id, gap_id=g.id, at=now(), message_sent=body))
        budget -= 1
        sent.append({"gap_ids": [g.id for g in gaps], "peer": peer, "body": body})
        r.emit("decision_sent", gap_ids=[g.id for g in gaps], peer=peer, body=body,
               combined=len(gaps) > 1)
    if deferred:
        r.emit("decision_deferred", gap_ids=deferred, reason="daily interrupt budget reached")
    return {"sent": len(sent), "messages": sent, "deferred": deferred,
            "interrupts_today": interrupts_today(), "budget": DAILY_INTERRUPT_BUDGET}


def apply_chief_reply(choice: str) -> dict:
    """Apply the chief's reply to the oldest interrupt awaiting an answer."""
    r = rt()
    d = dept()
    waiting = [g for g in r.store.list_gaps(d.id, {"needs_chief", "no_options"}) if g.decision_sent_at]
    recent_covered = [g for g in r.store.list_gaps(d.id, {"covered"}) if g.confirmed_at
                      and now() - g.confirmed_at <= timedelta(minutes=10) and g.covered_by in d.peers]
    if choice == "undo":
        if not recent_covered:
            return {"applied": False, "reason": "nothing to undo"}
        for g in recent_covered:
            g.status = "needs_chief"
            g.covered_by = None
            g.confirmed_at = None
            r.store.put_gap(g)
        r.sms.send(d.id, d.chief_phone, render("undone", **_slots(recent_covered[0])), "undone")
        r.emit("gap_status", gap_id=recent_covered[0].id, status="needs_chief", resolution="chief undid approval")
        return {"applied": True, "action": "undone", "gap_ids": [g.id for g in recent_covered]}
    if not waiting:
        return {"applied": False, "reason": "no decision pending"}

    # all gaps that were sent in the same text answer together
    oldest = min(waiting, key=lambda g: g.decision_sent_at)
    batch = [g for g in waiting if g.decision_sent_at == oldest.decision_sent_at]

    if choice == "1":
        covered, peer_name = [], None
        for g in batch:
            best = next((o for o in g.offers if o.can_cover), None)
            if not best:
                continue
            result = confirm_with_peer(g.id, best.from_dept)
            if result.get("accepted"):
                covered.append(g)
                peer_name = r.store.get_department(best.from_dept).short_name
        if not covered:
            return {"applied": False, "reason": "no offer to approve"}
        # A neighbour's agent can decline a confirmation, or its chief can be asked to approve it,
        # even after it offered. If the chief taps once for two windows and only one is confirmed,
        # saying "Done" would leave a critical window open with nobody knowing. Name what is still
        # open in the same message.
        still_open = [g for g in batch if g not in covered]
        if still_open:
            windows = ", ".join(f"{fmt_day(g.window_start)} {fmt_hour(g.window_start)}"
                                f"-{fmt_hour(g.window_end)}" for g in still_open)
            r.sms.send(d.id, d.chief_phone,
                       render("partly_approved", by=peer_name, open_windows=windows,
                              **_slots(covered[0])), "approved")
            r.emit("partly_approved", covered=[g.id for g in covered],
                   still_open=[g.id for g in still_open])
        else:
            r.sms.send(d.id, d.chief_phone,
                       render("approved", by=peer_name, **_slots(covered[0])), "approved")
        told = set()
        for g in covered:
            for mid in g.asked_member_ids:
                if mid in told:
                    continue
                m = r.store.get_member(d.id, mid)
                if not m.opted_out:
                    r.sms.send(d.id, m.phone, render("covered", by=peer_name, **_slots(g)), "covered", member_id=mid)
                    told.add(mid)
        action = (f"approved {peer_name} for {len(covered)} of {len(batch)} window(s)"
                  if still_open else f"approved {peer_name} for {len(covered)} window(s)")
    elif choice.startswith("2"):
        lines = [f"Other options for {fmt_day(oldest.window_start)}:"]
        idx = "abcdef"
        for i, o in enumerate(oldest.offers[:4]):
            peer = r.store.get_department(o.from_dept)
            lines.append(f"2{idx[i]} {peer.short_name}, {o.estimated_delay_min} min delay" if o.can_cover
                         else f"2{idx[i]} {peer.short_name}: declined ({o.reason_if_declined})")
        lines.append("Reply 1 for the best offer, or 3 to leave open.")
        r.sms.send(d.id, d.chief_phone, (f"{d.short_name}: " + "\n".join(lines))[:300], "options")
        action = "options sent"
    elif choice == "3":
        for g in batch:
            g.status = "left_open"
            g.next_check = now() + timedelta(hours=3)
            r.store.put_gap(g)
        r.sms.send(d.id, d.chief_phone,
                   render("left_open", dept=d.short_name, next_check=fmt_hour(batch[0].next_check)), "left_open")
        action = "left open"
    else:
        return {"applied": False, "reason": f"unrecognized choice {choice}"}

    for dec in r.store.list_decisions(d.id):
        if dec.gap_id in {g.id for g in batch} and not dec.reply:
            dec.reply, dec.action_taken = choice, action
    r.emit("chief_reply", gap_ids=[g.id for g in batch], choice=choice, action=action)
    return {"applied": True, "action": action, "gap_ids": [g.id for g in batch]}


@tool
def send_status(to_deputy: bool = False) -> dict:
    """Send the chief the on-demand status line for the next 7 days.

    Args:
        to_deputy: send to the deputy instead.
    """
    r = rt()
    d = dept()
    gaps = [g for g in r.store.list_gaps(d.id) if g.level.value in ("high", "critical") and g.window_end > now()
            and g.status != "covered"]
    if not gaps:
        body = render("status_clear", dept=d.short_name)
    else:
        lines = "".join(f"{fmt_day(g.window_start)} {fmt_hour(g.window_start)}-{fmt_hour(g.window_end)} "
                        f"{g.level.value.upper()} ({g.status.replace('_', ' ')}). " for g in gaps[:3])
        body = render("status", dept=d.short_name, n_gaps=len(gaps), gap_lines=lines)
    to = d.deputy_phone if to_deputy and d.deputy_phone else d.chief_phone
    r.sms.send(d.id, to, body, "status")
    return {"sent": True, "body": body}
