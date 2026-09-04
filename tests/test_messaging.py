from datetime import datetime

import pytest

from turnout.messaging import fmt_day, fmt_hour, render, templates


def test_all_templates_have_sender_slot():
    for k, v in templates().items():
        if k in {"held_prefix", "recommendation_offer"}:
            continue
        assert v.startswith("{dept}"), k


def test_fmt():
    assert fmt_hour(datetime(2026, 9, 10, 10)) == "10a"
    assert fmt_hour(datetime(2026, 9, 10, 14)) == "2p"
    assert fmt_hour(datetime(2026, 9, 10, 14, 30)) == "2:30p"
    assert fmt_day(datetime(2026, 9, 10)) == "Thu"


def test_poll_under_160():
    t = render("poll", dept="Millbrook VFC", day="Thu", start="8a", end="5p")
    assert len(t) <= 160


def test_decision_under_300_for_demo_case():
    t = render("decision", dept="Millbrook VFC", day="Thu", start="10a", end="2p", district="north",
               level="CRITICAL",
               explanation="1 to 2 calls expected, no driver operator, 100% chance nobody qualified responds, ice storm warning",
               recommendation="Riverton can cover, 9 min delay. Millbrook would owe 4 hrs")
    assert len(t) <= 300
    assert t.count("\n") == 3


def test_over_limit_raises():
    with pytest.raises(ValueError):
        render("poll", dept="X" * 200, day="Thu", start="8a", end="5p")
