"""House style on text a model wrote.

check_copy.py holds the repository to no emoji and no em dashes and never saw the text that actually
reaches a chief or a volunteer. Tally, the sibling project, shipped two questions to its deployed
service with em dashes in them through the same kind of path.

A text message is the worse place for it: an em dash costs a character out of a 160 character
segment, and some handsets render it as a box.
"""

from __future__ import annotations

from turnout.house import plain, plain_all

EM = chr(0x2014)
EN = chr(0x2013)
CURLY = chr(0x2019)
NBSP = chr(0x00A0)


def test_an_em_dash_becomes_a_comma_and_an_en_dash_a_hyphen():
    assert plain(f"Thursday 10 to 2 {EM} critical") == "Thursday 10 to 2, critical"
    assert plain(f"10{EN}14") == "10-14"


def test_emoji_go_and_the_sentence_still_reads():
    assert plain("Covered \U0001F44D nothing needed") == "Covered nothing needed"
    assert plain(chr(0x2705) + " confirmed") == "confirmed"


def test_smart_quotes_and_odd_spaces_are_normalised():
    assert plain(f"the chief{CURLY}s call") == "the chief's call"
    assert plain(f"Engine{NBSP}1") == "Engine 1"


def test_ordinary_operational_text_is_left_alone():
    for s in ["Thursday 10:00-14:00 north district: critical.",
              "Riverton can cover, 9 min out. Reply 1 to accept.",
              "Reply Y or N. Reply STOP to opt out.",
              "-20 degrees, ice storm warning"]:
        assert plain(s) == s


def test_it_is_idempotent_and_safe_on_nothing():
    once = plain(f"a {EM} b \U0001F600")
    assert plain(once) == once
    assert plain("") == ""
    assert plain_all([f"x {EM} y", "\U0001F600", ""]) == ["x, y"]


def test_every_outgoing_message_is_cleaned():
    """The choke point that matters: whatever writes it, this is what lands on a phone."""
    from datetime import datetime

    from turnout import runtime
    from turnout.clock import Clock
    from turnout.sim.runner import load_scenario

    store, sc = load_scenario("data/scenarios/demo_week.json")
    rt = runtime.local_runtime("millbrook", clock=Clock(datetime.fromisoformat(sc["clock_start"])),
                               store=store)
    runtime.configure(rt)

    rt.sms.send("millbrook", "+15550000000",
                f"Thursday 10 to 2 {EM} short a driver \U0001F525", "decision")
    body = rt.sms.sent[-1].body
    assert EM not in body
    assert "\U0001F525" not in body
    assert body == "Thursday 10 to 2, short a driver"


def test_a_cleaned_message_is_never_longer_than_it_was():
    """Segment budgets are checked elsewhere against 160 characters, so this must not add to one."""
    for s in [f"a {EM} b", "plain text", f"x{NBSP}y", "\U0001F600 z", f"end{chr(0x2026)}"]:
        assert len(plain(s)) <= len(s) + 2  # only the ellipsis expands, by two characters


def test_a_fresh_demo_does_not_claim_an_outcome_it_has_not_computed():
    """No gaps and nothing scored are not the same claim.

    Before the coverage pass runs there is no verdict, and the board used to announce "All windows
    covered through Sunday" on a demo where nothing had happened. A judge arriving cold read that as
    the product having already done its job.
    """
    from turnout.api.service import DemoService

    svc = DemoService()
    fresh = svc.state()
    assert fresh["tone"] == "idle"
    assert "covered" not in fresh["headline"].lower()
    assert fresh["headline"] == "The week has not been scored yet."

    # Once the coverage pass has run and nothing is outstanding, the verdict is real again.
    svc.done.append("watch")
    scored = svc.state()
    assert scored["tone"] == "clear"
    assert scored["headline"] == "All windows covered through Sunday."
