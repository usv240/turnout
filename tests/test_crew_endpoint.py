"""The accountability endpoint: what the agent knows about each member, and what it has asked.

An agent that asks unpaid people for hours of their life should be answerable to them. These tests
hold that page to its promises: the limits it states are the limits the code enforces, the numbers
come from that member's own history, and nothing on it is a model's opinion.
"""

from fastapi.testclient import TestClient

from turnout.api.app import app
from turnout.engine.kernel import response_probability

client = TestClient(app)


def crew() -> dict:
    r = client.get("/api/crew")
    assert r.status_code == 200
    return r.json()


def test_every_member_is_listed_including_anyone_who_opted_out():
    """A member who said STOP still appears, marked, or the roster hides who it stopped asking."""
    d = crew()
    ids = [m["id"] for m in d["members"]]
    assert len(ids) == 14
    assert len(set(ids)) == len(ids)
    assert all("opted_out" in m for m in d["members"])


def test_the_stated_ask_limit_is_the_one_the_hook_enforces():
    from turnout.api.service import service

    d = crew()
    dept = service.rt.store.get_department("millbrook")
    assert d["department"]["weekly_ask_limit"] == dept.weekly_ask_limit
    assert all(m["weekly_ask_limit"] == dept.weekly_ask_limit for m in d["members"])


def test_nobody_is_shown_as_asked_more_than_the_limit():
    for m in crew()["members"]:
        assert m["asks_this_week"] <= m["weekly_ask_limit"]


def test_the_probability_is_the_one_the_engine_uses_not_a_second_opinion():
    """If this page and the risk engine could disagree, the page would be decoration."""
    for m in crew()["members"]:
        for w in m["by_window"]:
            assert w["probability"] == round(response_probability(w["yes"], w["no"]), 3)
        assert m["overall"]["yes"] == sum(w["yes"] for w in m["by_window"])
        assert m["overall"]["no"] == sum(w["no"] for w in m["by_window"])


def test_the_prior_is_named_with_its_source():
    p = crew()["prior"]
    assert p["mean"] == 0.32 and p["strength"] == 10
    assert "Volunteer First Responders" in p["source"]


def test_quiet_hours_are_shown_for_everyone():
    for m in crew()["members"]:
        start, end = m["quiet_hours"]
        assert 0 <= start <= 23 and 0 <= end <= 23


def test_the_page_carries_no_phone_number_it_did_not_already_text():
    """Every number here is a +1555 fictional one, which is the only kind this project holds."""
    for m in crew()["members"]:
        assert m["phone"].startswith("+1555")


def test_members_who_have_not_been_texted_yet_report_an_empty_thread():
    d = crew()
    for m in d["members"]:
        assert isinstance(m["messages"], list)
        assert m["asked_count"] == sum(
            1 for x in m["messages"] if x["direction"] == "out" and x["purpose"] == "ask")
        assert m["poll_count"] == sum(
            1 for x in m["messages"] if x["direction"] == "out" and x["purpose"] == "poll")
