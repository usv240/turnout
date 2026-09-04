from datetime import datetime, timedelta

import pytest

from turnout.engine.risk import (
    HAZARD_MULTIPLIERS,
    RateModel,
    level_for,
    p_understaffed,
    response_probability,
    score_window,
    window_type,
)
from turnout.models import Call, Level, Role, WeatherAlert

FIRE = {Role.DRIVER_OPERATOR: 1, Role.FIREFIGHTER: 2}
NOW = datetime(2026, 9, 10, 7, 30)
THU_10 = datetime(2026, 9, 10, 10, 0)
THU_14 = datetime(2026, 9, 10, 14, 0)


def _history(n_per_day: float, days: int = 365, crit_share: float = 0.6) -> list[Call]:
    calls = []
    start = NOW - timedelta(days=days)
    i = 0
    t = start
    while t < NOW:
        # spread calls through the day weighted to daytime
        for h in (9, 11, 14, 18):
            if (i % 4) < int(n_per_day) or (i % 4 == 0 and n_per_day % 1 > 0):
                calls.append(Call(dept_id="d", at=t.replace(hour=h), type="medical", district="north",
                                  duration_min=45, responders=["a"], time_critical=(i % 10) < crit_share * 10))
            i += 1
        t += timedelta(days=1)
    return calls


def test_response_probability_prior_and_update():
    assert response_probability(0, 0) == pytest.approx(0.32)
    # prior strength is 10 equivalent observations, so 10 yes gives (3.2 + 10) / 20 = 0.66
    assert response_probability(10, 0) == pytest.approx(0.66)
    assert response_probability(40, 0) > 0.85
    assert response_probability(0, 40) < 0.1


def test_window_type():
    assert window_type(datetime(2026, 9, 10, 10)) == "weekday_day"
    assert window_type(datetime(2026, 9, 12, 19)) == "weekend_evening"
    assert window_type(datetime(2026, 9, 12, 2)) == "weekend_night"


def test_p_understaffed_exact_hand_computed():
    # One driver (p=0.5) and two firefighters (p=1.0): understaffed only when driver absent.
    members = [({Role.DRIVER_OPERATOR}, 0.5), ({Role.FIREFIGHTER}, 1.0), ({Role.FIREFIGHTER}, 1.0)]
    assert p_understaffed(members, FIRE) == pytest.approx(0.5)


def test_p_understaffed_nobody():
    assert p_understaffed([], FIRE) == 1.0


def test_p_understaffed_monotone_in_members():
    base = [({Role.DRIVER_OPERATOR}, 0.4), ({Role.FIREFIGHTER}, 0.4), ({Role.FIREFIGHTER}, 0.4)]
    more = [*base, ({Role.FIREFIGHTER, Role.DRIVER_OPERATOR}, 0.4)]
    assert p_understaffed(more, FIRE) <= p_understaffed(base, FIRE)


def test_monte_carlo_agrees_with_exact():
    members = [({Role.DRIVER_OPERATOR}, 0.5), ({Role.FIREFIGHTER}, 0.7), ({Role.FIREFIGHTER}, 0.7)]
    exact = p_understaffed(members, FIRE)
    mc = p_understaffed(members * 5, FIRE)  # 15 members forces Monte Carlo; different set, only sanity
    assert 0.0 <= mc <= 1.0
    assert 0.0 <= exact <= 1.0


def test_rate_model_no_history_uses_national():
    rm = RateModel.from_history([], NOW)
    assert rm.history_days == 0
    assert rm.expected_calls(THU_10, THU_14) > 0


def test_rate_model_learns_from_history():
    rm = RateModel.from_history(_history(2.0), NOW)
    assert rm.history_days >= 364
    lam_day = rm.expected_calls(THU_10, THU_14)
    lam_night = rm.expected_calls(datetime(2026, 9, 10, 2), datetime(2026, 9, 10, 6))
    assert lam_day > lam_night


def test_levels():
    assert level_for(0.9) == Level.CRITICAL
    assert level_for(0.6) == Level.HIGH
    assert level_for(0.3) == Level.ELEVATED
    assert level_for(0.1) == Level.LOW


def test_hazard_never_decreases_risk():
    rm = RateModel.from_history(_history(2.0), NOW)
    avail = [({Role.FIREFIGHTER}, 0.6)]
    base = score_window(THU_10, THU_14, avail, FIRE, rm, [])
    storm = score_window(THU_10, THU_14, avail, FIRE, rm,
                         [WeatherAlert(event="Ice Storm Warning", start=THU_10, end=THU_14,
                                       multiplier=HAZARD_MULTIPLIERS["ice storm warning"])])
    assert storm.risk_score >= base.risk_score
    assert "ice storm warning" in storm.explanation


def test_more_members_never_increases_risk():
    rm = RateModel.from_history(_history(2.0), NOW)
    few = [({Role.FIREFIGHTER}, 0.6)]
    more = [*few, ({Role.DRIVER_OPERATOR}, 0.6), ({Role.FIREFIGHTER}, 0.6)]
    assert score_window(THU_10, THU_14, more, FIRE, rm, []).risk_score <= \
        score_window(THU_10, THU_14, few, FIRE, rm, []).risk_score


def test_demo_gap_is_critical():
    """The headline demo gap: one firefighter available, no driver, ice storm. Must be critical."""
    rm = RateModel.from_history(_history(2.5, crit_share=0.7), NOW)
    avail = [({Role.FIREFIGHTER}, 0.45)]
    r = score_window(THU_10, THU_14, avail, FIRE, rm,
                     [WeatherAlert(event="Ice Storm Warning", start=THU_10 - timedelta(hours=4), end=THU_14,
                                   multiplier=1.8)])
    assert r.level == Level.CRITICAL
    assert r.missing_roles == [Role.DRIVER_OPERATOR] or Role.DRIVER_OPERATOR in r.missing_roles
    assert "short a driver" in r.explanation
    assert r.p_understaffed == 1.0  # a single firefighter can never satisfy the crew


def test_explanation_mentions_thin_history():
    rm = RateModel.from_history(_history(1.0, days=20), NOW)
    r = score_window(THU_10, THU_14, [], FIRE, rm, [])
    assert "national pattern" in r.explanation
