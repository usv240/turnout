"""The bring-your-own-window endpoint. Anyone can point the risk engine at their own Tuesday."""

from fastapi.testclient import TestClient

from turnout.api.app import app

client = TestClient(app)


def post(body: dict):
    return client.post("/api/risk/score", json=body)


def test_a_short_crew_in_an_ice_storm_is_critical():
    r = post({
        "window_start": "2026-09-10T10:00", "hours": 4,
        "available": [{"roles": ["firefighter"], "responds": 0.45}],
        "min_crew": {"driver_operator": 1, "firefighter": 2},
        "calls_per_day": 2.5, "weather": "ice storm warning",
    })
    assert r.status_code == 200
    d = r.json()
    assert d["level"] == "critical"
    assert d["inputs"]["p_understaffed"] == 1.0
    assert "driver_operator" in d["inputs"]["missing_roles"]
    assert "ice storm warning" in d["explanation"]


def test_a_full_crew_of_reliable_people_is_low():
    r = post({
        "window_start": "2026-09-13T02:00", "hours": 3,
        "available": [{"roles": ["driver_operator", "firefighter"], "responds": 0.98},
                      {"roles": ["firefighter"], "responds": 0.98},
                      {"roles": ["firefighter"], "responds": 0.98}],
        "calls_per_day": 1.0,
    })
    assert r.status_code == 200
    assert r.json()["level"] == "low"


def test_the_numbers_behind_the_answer_come_back():
    d = post({"available": [{"roles": ["firefighter"]}]}).json()
    for key in ("expected_calls", "hazard", "p_understaffed", "severity", "missing_roles"):
        assert key in d["inputs"]
    assert d["formula"].startswith("risk = 1 - exp(")
    assert "national" in d["note"]


def test_defaults_are_enough_to_get_an_answer():
    r = post({"available": [{"roles": ["firefighter"]}, {"roles": ["driver_operator"]}]})
    assert r.status_code == 200
    assert r.json()["window"]["hours"] == 4


def test_an_unknown_weather_alert_lists_the_ones_it_knows():
    r = post({"available": [{"roles": ["firefighter"]}], "weather": "light drizzle"})
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert "ice storm warning" in detail["known_alerts"]


def test_an_unknown_role_is_refused_with_the_roles_it_knows():
    r = post({"available": [{"roles": ["astronaut"]}]})
    assert r.status_code == 400
    assert "firefighter" in r.json()["detail"]["known_roles"]


def test_nobody_available_is_refused_rather_than_scored():
    assert post({"available": []}).status_code == 400


def test_a_response_probability_outside_zero_to_one_is_refused():
    r = post({"available": [{"roles": ["firefighter"], "responds": 4}]})
    assert r.status_code == 400
    assert "between 0 and 1" in r.json()["detail"]["error"]


def test_more_people_lowers_the_score_for_the_same_window():
    base = {"window_start": "2026-09-10T10:00", "calls_per_day": 2.5}
    few = post({**base, "available": [{"roles": ["firefighter"]}]}).json()["risk_score"]
    many = post({**base, "available": [{"roles": ["driver_operator"]}, {"roles": ["firefighter"]},
                                       {"roles": ["firefighter"]}]}).json()["risk_score"]
    assert many <= few
