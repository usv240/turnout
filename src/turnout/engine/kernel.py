"""The arithmetic behind a risk score, as plain Python over plain types.

This module is deliberately dependency free: standard library only, no pydantic, no project
imports. That is what lets the identical source run in two places.

Locally it is imported and called. On AWS the source of this file is uploaded into an Amazon Bedrock
AgentCore Code Interpreter session and the same functions are called there, so "the risk engine runs
as code in Code Interpreter" is a statement about this exact file rather than a reimplementation of
it that might drift.

Roles are plain strings. Crew requirements are {role: count}. Nothing here knows what a fire
department is; it knows matching and probability.
"""

from __future__ import annotations

import math
import random
from itertools import product

SCALE = 3.0
"""Chosen so that roughly half of one expected unanswered time-critical call reads as critical. A
four hour window in a department running 1.6 calls a day expects well under one call, so a raw
arrival rate would never reach a level a chief would act on. This constant is a modelling choice,
not something derived from data."""

PRIOR_MEAN = 0.32
PRIOR_STRENGTH = 10.0

CRITICAL, HIGH, ELEVATED = 0.75, 0.50, 0.25


def response_probability(yes: int, no: int) -> float:
    """Posterior mean of Beta(alpha, beta) with prior mean 0.32 and strength 10.

    The prior is the middle of the 17 to 47 percent range reported for volunteer first responders in
    Predictive Dispatch of Volunteer First Responders, 2023.
    """
    a0 = PRIOR_MEAN * PRIOR_STRENGTH
    b0 = (1 - PRIOR_MEAN) * PRIOR_STRENGTH
    return (a0 + yes) / (a0 + b0 + yes + no)


def slots_for(min_crew: dict) -> list:
    out = []
    for role, n in min_crew.items():
        out.extend([role] * int(n))
    return out


def max_matching(member_roles: list, slots: list) -> tuple:
    """Kuhn's algorithm. One person fills at most one slot, however many roles they hold."""
    slot_to_member = [None] * len(slots)

    def try_assign(m: int, seen: list) -> bool:
        for s, role in enumerate(slots):
            if role in member_roles[m] and not seen[s]:
                seen[s] = True
                if slot_to_member[s] is None or try_assign(slot_to_member[s], seen):
                    slot_to_member[s] = m
                    return True
        return False

    matched = 0
    for m in range(len(member_roles)):
        if try_assign(m, [False] * len(slots)):
            matched += 1
    return matched, slot_to_member


def missing_roles(member_roles: list, min_crew: dict) -> list:
    """Roles that cannot be filled. Empty means the crew requirement is satisfiable."""
    slots = slots_for(min_crew)
    if not slots:
        return []
    matched, assignment = max_matching(member_roles, slots)
    if matched == len(slots):
        return []
    return [slots[i] for i, m in enumerate(assignment) if m is None]


def is_feasible(member_roles: list, min_crew: dict) -> bool:
    return not missing_roles(member_roles, min_crew)


def p_understaffed(members: list, min_crew: dict, rng_seed: int = 7,
                   monte_carlo_draws: int = 10_000) -> float:
    """Probability that the people who actually turn out cannot make the minimum crew.

    members: list of (roles, probability). Exact enumeration up to twelve people, Monte Carlo above,
    because 2^13 subsets is where the exact sum stops being instant.
    """
    n = len(members)
    if n == 0:
        return 1.0
    if n <= 12:
        total = 0.0
        for mask in product([0, 1], repeat=n):
            p = 1.0
            roles = []
            for present, (r, pr) in zip(mask, members, strict=True):
                p *= pr if present else (1 - pr)
                if present:
                    roles.append(set(r))
            if p == 0.0:
                continue
            if not is_feasible(roles, min_crew):
                total += p
        return min(1.0, max(0.0, total))
    rng = random.Random(rng_seed)
    fails = 0
    for _ in range(monte_carlo_draws):
        roles = [set(r) for (r, pr) in members if rng.random() < pr]
        if not is_feasible(roles, min_crew):
            fails += 1
    return fails / monte_carlo_draws


def level_for(score: float, critical: float = CRITICAL, high: float = HIGH,
              elevated: float = ELEVATED) -> str:
    if score >= critical:
        return "critical"
    if score >= high:
        return "high"
    if score >= elevated:
        return "elevated"
    return "low"


def risk_score(expected_calls: float, hazard: float, p_under: float, severity: float) -> float:
    return 1 - math.exp(-SCALE * (expected_calls * hazard) * p_under * severity)


def score(payload: dict) -> dict:
    """The whole calculation from one JSON-shaped input, so the remote call is a single round trip.

    payload: {
      "members": [[["firefighter"], 0.45], ...],   roles and response probability
      "min_crew": {"driver_operator": 1, "firefighter": 2},
      "expected_calls": 0.373, "hazard": 1.8, "severity": 0.825,
      "thresholds": [0.75, 0.50, 0.25]
    }
    """
    members = [(set(r), float(p)) for r, p in payload["members"]]
    min_crew = {k: int(v) for k, v in payload["min_crew"].items()}
    pu = p_understaffed(members, min_crew)
    missing = missing_roles([r for r, _ in members], min_crew)
    lam = float(payload["expected_calls"])
    hazard = float(payload["hazard"])
    sev = float(payload["severity"])
    s = risk_score(lam, hazard, pu, sev)
    crit, high, elev = payload.get("thresholds", [CRITICAL, HIGH, ELEVATED])
    return {
        "p_understaffed": round(pu, 6),
        "missing_roles": missing,
        "risk_score": round(s, 6),
        "level": level_for(s, crit, high, elev),
        "scale": SCALE,
    }
