"""Deterministic end-to-end of the tools, no model calls except the one free-text reply the rules cannot read.

These tests pin the demo scenario: the exact gaps, who Closer may ask, what each peer answers, and the
policies that must hold in code rather than in a prompt.
"""

from datetime import datetime

import pytest

from turnout.agents.peer_service import evaluate_request, travel_minutes
from turnout.agents.roll_call import handle_inbound, send_daily_polls
from turnout.models import CoverageRequest, Level, Role
from turnout.sim.runner import setup
from turnout.tools.chief import DAILY_INTERRUPT_BUDGET, interrupts_today, send_decisions
from turnout.tools.closer import check_asks, rank_candidates, send_ask
from turnout.tools.coverage import compute_gaps
from turnout.tools.peers import request_coverage_from_peers
from turnout.tools.sms import flush_held

SCENARIO = "data/scenarios/demo_week.json"
THU10 = "millbrook-20260910T10-fire"
THU14 = "millbrook-20260910T14-fire"


@pytest.fixture
def rt():
    r, _ = setup(SCENARIO)
    return r


def _advance(r, until: datetime):
    while r.clock.now() < until:
        r.clock.advance(minutes=15)
        flush_held(r)
        r.sms.deliver_due()
        r.dept_id = "millbrook"


def _polled(r):
    r.dept_id = "millbrook"
    send_daily_polls()
    _advance(r, datetime(2026, 9, 9, 7, 30))
    return compute_gaps()


def test_travel_minutes_demo_topology(rt):
    mb = rt.store.get_department("millbrook")
    rv = rt.store.get_department("riverton")
    cd = rt.store.get_department("cedar")
    assert 8 <= travel_minutes(rv.coordinates, mb.coordinates) <= 10
    assert travel_minutes(cd.coordinates, mb.coordinates) > 12


def test_the_demo_week_produces_exactly_two_actionable_gaps(rt):
    """Two windows cannot form a crew and are acted on. One is thin but coverable, so it is only shown."""
    gaps = _polled(rt)
    actionable = [g for g in gaps if g.level.value in ("high", "critical") and g.status != "thin"]
    assert [g.id for g in actionable] == [THU10, THU14], [(g.id, g.level.value, g.status) for g in gaps]

    thin = [g for g in gaps if g.status == "thin"]
    assert [g.id for g in thin] == ["millbrook-20260910T08-fire"]
    assert thin[0].inputs.missing_roles == []  # a crew exists on paper
    assert "chance nobody qualified responds" in thin[0].explanation

    thu10 = next(g for g in gaps if g.id == THU10)
    assert thu10.level == Level.CRITICAL
    assert thu10.window_start.hour == 10 and thu10.window_end.hour == 14
    assert Role.DRIVER_OPERATOR in thu10.inputs.missing_roles
    assert "ice storm warning" in thu10.explanation
    assert "short a driver" in thu10.explanation
    assert thu10.inputs.hazard == pytest.approx(1.8)
    assert thu10.inputs.available_member_ids == ["millbrook-m03"]

    thu14 = next(g for g in gaps if g.id == THU14)
    assert thu14.level == Level.HIGH
    assert thu10.risk_score > thu14.risk_score


def test_closer_never_sees_a_thin_window(rt):
    """There is nobody left to ask about a thin window, so it must not reach Closer's work list."""
    from turnout.tools.coverage import list_gaps

    _polled(rt)
    assert all(g["id"] != "millbrook-20260910T08-fire" for g in list_gaps(min_level="high"))
    assert any(g["id"] == "millbrook-20260910T08-fire" for g in list_gaps(statuses=["thin"], min_level="high"))


def test_closer_candidates_exclude_everyone_who_already_answered(rt):
    _polled(rt)
    cands = rank_candidates(THU10)
    ids = [c["member_id"] for c in cands]
    assert ids[0] == "millbrook-m12"  # highest predicted yes for a weekday daytime window
    assert "millbrook-m06" in ids and "millbrook-m09" in ids
    assert "millbrook-m03" not in ids  # said yes
    assert "millbrook-m08" not in ids  # said no
    assert "millbrook-m13" not in ids  # free text, read as no by the model
    assert all(set(c["fills"]) & {"driver_operator", "firefighter"} for c in cands)


def test_send_ask_writes_the_message_itself(rt):
    _polled(rt)
    res = send_ask(THU10, "millbrook-m12")
    assert res["sent"] is True
    assert res["body"] == ("Millbrook VFC: Thu 10a-2p needs a driver. You usually can. Reply Y or N. "
                           "If Y, you are on the board and the chief is told.")
    assert len(res["body"]) <= 160
    assert rt.store.get_gap("millbrook", THU10).status == "asking_members"


def test_bad_gap_id_is_an_error_not_a_false_success(rt):
    _polled(rt)
    assert check_asks("gap_1")["next_action"] == "error"
    assert THU10 in check_asks("gap_1")["valid_gap_ids"]
    assert send_ask("made_up_id", "millbrook-m12")["sent"] is False


def test_quiet_hours_hold_the_ask_and_the_weekly_limit_blocks_it(rt):
    rt.dept_id = "millbrook"
    send_daily_polls()
    rt.clock.set(datetime(2026, 9, 9, 7, 0))  # m06's quiet hours run to 08:00
    compute_gaps()
    res = send_ask(THU10, "millbrook-m06")
    assert res["sent"] is False and res["held_until"].startswith("2026-09-09T08:00")
    assert res["body"].startswith("Sent after your quiet hours.")
    m = rt.store.get_member("millbrook", "millbrook-m06")
    assert m.asks_this_week == 1
    m.asks_this_week = 2  # at the department limit
    rt.store.put_member(m)
    assert rank_candidates(THU10) and all(c["member_id"] != "millbrook-m06" for c in rank_candidates(THU10))


def test_peer_evaluation_riverton_offers_cedar_declines(rt):
    req = CoverageRequest(request_id="r1", from_dept="millbrook", window_start=datetime(2026, 9, 10, 10),
                          window_end=datetime(2026, 9, 10, 14), district="north",
                          roles_needed=[Role.DRIVER_OPERATOR], risk_level=Level.CRITICAL,
                          risk_explanation="test", expires_at=datetime(2026, 9, 10, 9))
    rt.dept_id = "riverton"
    offer = evaluate_request(req)
    assert offer.can_cover and offer.estimated_delay_min <= 10 and offer.auto_approved
    rt.dept_id = "cedar"
    offer = evaluate_request(req)
    assert not offer.can_cover
    assert "risk" in offer.reason_if_declined or "spare" in offer.reason_if_declined


def test_a2a_round_trip_ranks_riverton_first_and_records_cedars_reason(rt):
    _polled(rt)
    g = rt.store.get_gap("millbrook", THU10)
    g.status = "members_declined"
    rt.store.put_gap(g)
    out = request_coverage_from_peers(THU10)
    assert [o["peer"] for o in out["ranked"]] == ["riverton"]
    assert out["declined"][0]["peer"] == "cedar"
    assert rt.store.get_gap("millbrook", THU10).status == "needs_chief"


def test_two_gaps_one_peer_become_one_interrupt(rt):
    _polled(rt)
    for gid in (THU10, THU14):
        g = rt.store.get_gap("millbrook", gid)
        g.status = "members_declined"
        rt.store.put_gap(g)
        request_coverage_from_peers(gid)
    out = send_decisions()
    assert out["sent"] == 1, out
    body = out["messages"][0]["body"]
    assert "2 windows: 10a-2p and 2p-5p" in body
    assert "Riverton F&R can cover, 9 min delay" in body
    assert len(body) <= 300
    assert interrupts_today() == 1


def test_one_approval_covers_both_windows_and_moves_the_ledger(rt):
    _polled(rt)
    for gid in (THU10, THU14):
        g = rt.store.get_gap("millbrook", gid)
        g.status = "members_declined"
        rt.store.put_gap(g)
        request_coverage_from_peers(gid)
    send_decisions()
    chief = rt.store.get_department("millbrook").chief_phone
    handle_inbound(chief, "1")
    assert rt.store.get_gap("millbrook", THU10).covered_by == "riverton"
    assert rt.store.get_gap("millbrook", THU14).covered_by == "riverton"
    assert rt.store.ledger_balance("millbrook", "riverton") == pytest.approx(7.0)
    assert rt.store.ledger_balance("riverton", "millbrook") == pytest.approx(-7.0)


def test_interrupt_budget_defers_the_overflow(rt):
    _polled(rt)
    d = rt.store.get_department("millbrook")
    for _ in range(DAILY_INTERRUPT_BUDGET):
        rt.sms.send("millbrook", d.chief_phone, "x", "decision")
    for gid in (THU10, THU14):
        g = rt.store.get_gap("millbrook", gid)
        g.status = "members_declined"
        rt.store.put_gap(g)
        request_coverage_from_peers(gid)
    out = send_decisions()
    assert out["sent"] == 0 and out["deferred"]


def test_stop_is_honored(rt):
    rt.dept_id = "millbrook"
    m = rt.store.list_members("millbrook")[0]
    handle_inbound(m.phone, "STOP")
    assert rt.store.get_member("millbrook", m.id).opted_out
    assert "opted out" in rt.store.list_messages("millbrook", m.phone)[-1].body


def test_free_text_reply_is_escalated_to_the_model(rt):
    """m13 replies with prose the rule parser cannot read, so it goes to the model."""
    _polled(rt)
    events = [e for e in rt.trace if e["kind"] == "roll_call_llm"]
    assert any(e["member_id"] == "millbrook-m13" for e in events), events


def test_an_ambiguous_reply_never_becomes_availability(rt):
    """m13 says "depends on the kids, probably not". Whatever the model makes of that, it must not
    end up on the board as someone who is coming.

    This is the property worth testing. Asserting that the model always reads that sentence as a no
    would be asserting something no model guarantees, and the earlier version of this test failed
    intermittently for exactly that reason. Recording availability that is not really there is the
    dangerous direction: the board looks covered and nobody turns out."""
    _polled(rt)
    avail = rt.store.list_availability("millbrook", datetime(2026, 9, 10), datetime(2026, 9, 11))
    m13 = [a for a in avail if a.member_id == "millbrook-m13"]
    assert not [a for a in m13 if a.status in ("available", "partial")], m13
