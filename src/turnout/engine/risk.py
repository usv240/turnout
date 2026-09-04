"""The risk engine. Deterministic, explainable, cited.

risk = 1 - exp(-SCALE * (expected_calls * hazard) * p_understaffed * severity)

SCALE is 3.0, chosen so that about half of one expected unanswered time-critical call in a window
scores as critical (0.75). Small departments see fewer than one call in most four-hour windows,
and a chief still treats an uncovered window in an ice storm as critical; the scale encodes that.

- expected_calls: from the department's own call history by hour-of-day and day-of-week,
  smoothed toward a national-shaped profile when history is thin.
- p_understaffed: probability that the members who actually respond cannot satisfy the
  minimum crew. Per-member response probabilities are Beta posteriors with a prior mean
  of 0.32, the middle of the 17 to 47 percent range reported for volunteer first responders
  (Predictive Dispatch of Volunteer First Responders, 2023, PMC10716760).
- hazard: product of active weather alert multipliers.
- severity: share of time-critical call types in this window's history, scaled to [0.5, 1.0].
"""

from __future__ import annotations

import math
import random
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import product

from turnout.engine.feasibility import is_feasible, missing_roles
from turnout.models import Call, Level, Role, WeatherAlert

# Hour-of-day weights shaped like the national fire department call pattern:
# a daytime plateau with peaks late morning and early evening, a deep overnight trough.
NATIONAL_HOUR_PROFILE = [
    0.45, 0.38, 0.33, 0.30, 0.30, 0.38, 0.55, 0.80, 1.00, 1.15, 1.25, 1.25,
    1.20, 1.20, 1.20, 1.25, 1.30, 1.35, 1.30, 1.15, 1.00, 0.85, 0.70, 0.55,
]
NATIONAL_DOW_PROFILE = [1.02, 1.00, 1.00, 1.00, 1.05, 1.00, 0.93]  # Monday .. Sunday
NATIONAL_MONTH_PROFILE = [1.05, 0.98, 1.00, 0.98, 1.00, 1.02, 1.08, 1.06, 1.00, 0.98, 0.98, 1.05]

HAZARD_MULTIPLIERS = {
    "ice storm warning": 1.8,
    "winter storm warning": 1.6,
    "blizzard warning": 1.8,
    "heat advisory": 1.4,
    "excessive heat warning": 1.6,
    "red flag warning": 2.0,
    "high wind warning": 1.3,
    "flood warning": 1.5,
    "flash flood warning": 1.6,
    "severe thunderstorm warning": 1.4,
    "tornado warning": 2.0,
}

SCALE = 3.0
PRIOR_MEAN = 0.32
PRIOR_STRENGTH = 10.0  # equivalent observations behind the prior
SMOOTHING_DAYS = 90.0  # history shorter than this leans on the national profile


def hazard_multiplier(event: str) -> float:
    return HAZARD_MULTIPLIERS.get(event.strip().lower(), 1.0)


def window_type(dt: datetime) -> str:
    weekend = dt.weekday() >= 5
    h = dt.hour
    if 7 <= h < 17:
        part = "day"
    elif 17 <= h < 22:
        part = "evening"
    else:
        part = "night"
    return f"{'weekend' if weekend else 'weekday'}_{part}"


def response_probability(yes: int, no: int) -> float:
    """Posterior mean of a Beta(alpha, beta) with prior mean 0.32 and strength 10."""
    alpha0 = PRIOR_MEAN * PRIOR_STRENGTH
    beta0 = (1 - PRIOR_MEAN) * PRIOR_STRENGTH
    return (alpha0 + yes) / (alpha0 + beta0 + yes + no)


@dataclass
class RateModel:
    """Expected calls per hour for a department, learned from history and smoothed."""

    history_days: int
    base_per_hour: float  # overall mean calls per hour
    hour_weights: list[float]
    dow_weights: list[float]
    month_weights: list[float]
    severity_by_hour: list[float]  # share of time-critical calls by hour, smoothed

    @classmethod
    def from_history(cls, calls: list[Call], now: datetime, national_base_per_day: float = 1.6) -> "RateModel":
        if not calls:
            return cls(0, national_base_per_day / 24, NATIONAL_HOUR_PROFILE, NATIONAL_DOW_PROFILE,
                       NATIONAL_MONTH_PROFILE, [0.65] * 24)
        earliest = min(c.at for c in calls)
        days = max(1, (now - earliest).days)
        w = min(1.0, days / SMOOTHING_DAYS)  # trust in own history
        base = len(calls) / days / 24

        hour_counts = [0] * 24
        dow_counts = [0] * 7
        month_counts = [0] * 12
        crit_by_hour = [0] * 24
        for c in calls:
            hour_counts[c.at.hour] += 1
            dow_counts[c.at.weekday()] += 1
            month_counts[c.at.month - 1] += 1
            if c.time_critical:
                crit_by_hour[c.at.hour] += 1

        def norm(counts: list[int]) -> list[float]:
            total = sum(counts)
            n = len(counts)
            if total == 0:
                return [1.0] * n
            return [(x / total) * n for x in counts]

        own_hour, own_dow, own_month = norm(hour_counts), norm(dow_counts), norm(month_counts)
        hour_w = [w * o + (1 - w) * n for o, n in zip(own_hour, NATIONAL_HOUR_PROFILE)]
        dow_w = [w * o + (1 - w) * n for o, n in zip(own_dow, NATIONAL_DOW_PROFILE)]
        month_w = [w * o + (1 - w) * n for o, n in zip(own_month, NATIONAL_MONTH_PROFILE)]
        sev = []
        for h in range(24):
            if hour_counts[h] >= 5:
                sev.append(crit_by_hour[h] / hour_counts[h])
            else:
                sev.append(0.65)
        base = w * base + (1 - w) * (national_base_per_day / 24)
        return cls(days, base, hour_w, dow_w, month_w, sev)

    def expected_calls(self, start: datetime, end: datetime) -> float:
        total = 0.0
        t = start
        while t < end:
            step = min(timedelta(hours=1), end - t)
            frac = step.total_seconds() / 3600
            total += self.base_per_hour * self.hour_weights[t.hour] * self.dow_weights[t.weekday()] \
                * self.month_weights[t.month - 1] * frac
            t += step
        return total

    def severity(self, start: datetime, end: datetime) -> float:
        hours = []
        t = start
        while t < end:
            hours.append(self.severity_by_hour[t.hour])
            t += timedelta(hours=1)
        share = sum(hours) / len(hours) if hours else 0.65
        return 0.5 + 0.5 * share  # scale [0,1] share into [0.5, 1.0]


def p_understaffed(
    members: list[tuple[set[Role], float]],
    min_crew: dict[Role, int],
    rng_seed: int = 7,
    monte_carlo_draws: int = 10_000,
) -> float:
    """Probability that the responding subset cannot satisfy min_crew.

    members: list of (roles, response_probability). Exact enumeration for n <= 12, Monte Carlo otherwise.
    """
    n = len(members)
    if n == 0:
        return 1.0
    if n <= 12:
        total = 0.0
        for mask in product([0, 1], repeat=n):
            p = 1.0
            roles: list[set[Role]] = []
            for present, (r, pr) in zip(mask, members):
                p *= pr if present else (1 - pr)
                if present:
                    roles.append(r)
            if p == 0.0:
                continue
            if not is_feasible(roles, min_crew):
                total += p
        return min(1.0, max(0.0, total))
    rng = random.Random(rng_seed)
    fails = 0
    for _ in range(monte_carlo_draws):
        roles = [r for (r, pr) in members if rng.random() < pr]
        if not is_feasible(roles, min_crew):
            fails += 1
    return fails / monte_carlo_draws


@dataclass
class RiskResult:
    expected_calls: float
    p_understaffed: float
    hazard: float
    hazard_names: list[str]
    severity: float
    missing_roles: list[Role]
    risk_score: float
    level: Level
    explanation: str
    history_days: int


def level_for(score: float, critical: float = 0.75, high: float = 0.50, elevated: float = 0.25) -> Level:
    if score >= critical:
        return Level.CRITICAL
    if score >= high:
        return Level.HIGH
    if score >= elevated:
        return Level.ELEVATED
    return Level.LOW


def score_window(
    start: datetime,
    end: datetime,
    available: list[tuple[set[Role], float]],
    min_crew: dict[Role, int],
    rate: RateModel,
    alerts: list[WeatherAlert],
    thresholds: tuple[float, float, float] = (0.75, 0.50, 0.25),
) -> RiskResult:
    lam = rate.expected_calls(start, end)
    active = [a for a in alerts if a.start < end and a.end > start]
    hazard = 1.0
    names: list[str] = []
    for a in active:
        hazard *= a.multiplier
        names.append(a.event)
    sev = rate.severity(start, end)
    pu = p_understaffed(available, min_crew)
    missing = missing_roles([r for r, _ in available], min_crew)
    score = 1 - math.exp(-SCALE * (lam * hazard) * pu * sev)
    lvl = level_for(score, *thresholds)

    exp_calls = lam * hazard
    if exp_calls < 0.05:
        calls_txt = "calls unlikely"
    elif exp_calls < 0.75:
        calls_txt = "under 1 call expected"
    else:
        lo, hi = max(1, int(round(exp_calls - 0.5))), int(math.ceil(exp_calls + 0.5))
        calls_txt = f"{lo} to {hi} calls expected" if lo != hi else f"{lo} call expected"
    words = {"driver_operator": "a driver", "firefighter": "a firefighter", "emt": "an EMT", "officer": "an officer"}
    if missing:
        counts = Counter(r.value for r in missing)
        bits = []
        for role, n in counts.items():
            bits.append(words.get(role, role) if n == 1 else f"{n} {words.get(role, role).split(' ', 1)[1]}s")
        miss_txt = "short " + " and ".join(bits)
        parts = [calls_txt, miss_txt]
    elif not available:
        parts = [calls_txt, "nobody available"]
    else:
        parts = [calls_txt, f"{int(round(pu * 100))}% chance nobody qualified responds"]
    if names:
        parts.append(", ".join(n.lower() for n in names))
    if rate.history_days < SMOOTHING_DAYS:
        parts.append("estimate leans on national pattern")
    explanation = ", ".join(parts)
    return RiskResult(round(lam, 3), round(pu, 3), round(hazard, 3), names, round(sev, 3), missing,
                      round(score, 3), lvl, explanation, rate.history_days)
