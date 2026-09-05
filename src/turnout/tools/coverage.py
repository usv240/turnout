"""Coverage and gap tools. The Watch agent's heavy lifting lives here, deterministically.

How coverage is computed
1. For every hour in the horizon, build the set of members who could respond, each with their
   response probability. If the department asked about that hour (any availability record covers it),
   only members who said available or partial count. If nobody was asked, every active member counts at
   their historical probability, which is how pager-based volunteer response works outside polled hours.
2. Check whether that set can fill the minimum crew on paper (exact bipartite matching).
3. Group hours into windows that never cross a shift boundary (06, 10, 14, 17, 22). Hours that are
   infeasible on paper form one kind of window; feasible hours form another.
4. Score every window with the risk engine. Infeasible windows are always stored as gaps. Feasible windows
   are stored as gaps only when their risk is elevated or above (thin on paper, likely to fail).
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta

from strands import tool

from turnout.engine.feasibility import is_feasible
from turnout.engine.risk import RateModel, response_probability, score_window, window_type
from turnout.models import Gap, Level, Member, ResponseStats, RiskInputs
from turnout.tools.common import dept, now, parse_dt, rt

# Shift boundaries. A gap window never crosses one, so gaps read like a chief's day: 06-10, 10-14, 14-17, 17-22, 22-06.
BLOCK_EDGES = (6, 10, 14, 17, 22)


def _asked_about(recs, hour: datetime) -> bool:
    return any(a.window_start <= hour < a.window_end for a in recs)


def _available_at(members: list[Member], recs, hour: datetime) -> list[tuple[Member, float]]:
    asked = _asked_about(recs, hour)
    out = []
    for m in members:
        if m.opted_out:
            continue
        s = m.response_stats.get(window_type(hour), ResponseStats())
        p = response_probability(s.yes, s.no)
        if not asked:
            out.append((m, p))
            continue
        for a in recs:
            if a.member_id == m.id and a.status in ("available", "partial") and a.window_start <= hour < a.window_end:
                out.append((m, p))
                break
    return out


def _dominant_district(d, calls, start: datetime, end: datetime) -> str:
    c = Counter(c.district for c in calls if start.time() <= c.at.time() < end.time())
    return c.most_common(1)[0][0] if c else d.districts[0]


class _CachedRisk:
    """score_window with p_understaffed memoized by availability signature (huge speedup for 20+ members)."""

    def __init__(self, min_crew, rate, alerts, thresholds, use_agentcore: bool = False):
        self.min_crew, self.rate, self.alerts, self.thresholds = min_crew, rate, alerts, thresholds
        self.use_agentcore = use_agentcore
        self.cache: dict[tuple, float] = {}

    def score(self, start, end, avail):
        """Compute once per distinct set of available people, then reuse.

        Order matters. An earlier version computed the probability locally and passed it in, which
        meant the AgentCore path was never taken at all: every window came back local_cached. The
        first window for a given set of people now goes through the real path, AgentCore included,
        and only the repeats reuse it.
        """
        sig = tuple(sorted((m.id, round(p, 3)) for m, p in avail))
        members = [(set(m.roles), p) for m, p in avail]
        if sig not in self.cache:
            first = score_window(start, end, members, self.min_crew, self.rate, self.alerts,
                                 self.thresholds, use_agentcore=self.use_agentcore)
            self.cache[sig] = first.p_understaffed
            return first
        return score_window(start, end, members, self.min_crew, self.rate, self.alerts,
                            self.thresholds, use_agentcore=self.use_agentcore,
                            p_understaffed_override=self.cache[sig])


def compute_gaps(days: int = 7, apparatus: str = "fire") -> list[Gap]:
    r = rt()
    d = dept()
    t0 = now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    horizon = t0 + timedelta(days=days)
    members = r.store.list_members(d.id)
    recs = r.store.list_availability(d.id, t0, horizon)
    calls = r.store.list_calls(d.id, now() - timedelta(days=365))
    rate = RateModel.from_history(calls, now())
    alerts = r.weather.active_alerts(d.weather_zone, t0, horizon)
    min_crew = d.min_crew.fire if apparatus == "fire" else d.min_crew.ems
    scorer = _CachedRisk(min_crew, rate, alerts,
                         (r.settings.risk_critical, r.settings.risk_high, r.settings.risk_elevated),
                         use_agentcore=r.settings.use_agentcore)

    # hourly availability and paper feasibility
    hours: list[datetime] = []
    avail_by_hour: dict[datetime, list[tuple[Member, float]]] = {}
    feasible_by_hour: dict[datetime, bool] = {}
    t = t0
    while t < horizon:
        av = _available_at(members, recs, t)
        avail_by_hour[t] = av
        feasible_by_hour[t] = is_feasible([set(m.roles) for m, _ in av], min_crew)
        hours.append(t)
        t += timedelta(hours=1)

    # Windows are shift blocks, the unit a chief actually thinks in. A block is a gap when any hour in it
    # cannot fill the crew, and it is scored at its worst hour, so partial availability inside a block
    # (someone who can only do the morning) makes the block riskier rather than splitting it in two.
    windows: list[tuple[datetime, datetime, bool]] = []
    for h in hours:
        same_block = windows and windows[-1][1] == h and h.hour not in BLOCK_EDGES
        # hours we asked about and hours we did not are different kinds of information; never mix them
        if same_block and _asked_about(recs, h) != _asked_about(recs, windows[-1][0]):
            same_block = False
        if same_block:
            windows[-1] = (windows[-1][0], h + timedelta(hours=1), windows[-1][2] and feasible_by_hour[h])
        else:
            windows.append((h, h + timedelta(hours=1), feasible_by_hour[h]))

    existing = {g.id: g for g in r.store.list_gaps(d.id)}
    live_ids: set[str] = set()
    gaps: list[Gap] = []
    for start, end, feasible in windows:
        # conservative: the hour with the fewest potential responders represents the window
        block_hours = [h for h in hours if start <= h < end]
        infeasible_hours = [h for h in block_hours if not feasible_by_hour[h]]
        rep_hour = min(infeasible_hours or block_hours, key=lambda h: len(avail_by_hour[h]))
        av = avail_by_hour[rep_hour]
        res = scorer.score(start, end, av)
        if feasible and res.level in (Level.LOW, Level.ELEVATED):
            continue
        gid = f"{d.id}-{start:%Y%m%dT%H}-{apparatus}"
        live_ids.add(gid)
        prev = existing.get(gid)
        gap = Gap(
            id=gid, dept_id=d.id, window_start=start, window_end=end,
            district=_dominant_district(d, calls, start, end), apparatus=apparatus,
            inputs=RiskInputs(expected_calls=res.expected_calls, p_understaffed=res.p_understaffed,
                              hazard=res.hazard, hazard_names=res.hazard_names, severity=res.severity,
                              missing_roles=res.missing_roles, available_member_ids=[m.id for m, _ in av],
                              history_days=res.history_days, ran_in=res.ran_in,
                              fallback_reason=res.fallback_reason),
            risk_score=res.risk_score, level=res.level, explanation=res.explanation,
            status="thin" if feasible else "open",
        )
        if prev is not None:
            for f in ("status", "resolution", "covered_by", "asked_member_ids", "asked_at", "next_check",
                      "request_id", "offers", "chosen_peer", "decision_sent_at", "escalated", "confirmed_at"):
                setattr(gap, f, getattr(prev, f))
        r.store.put_gap(gap)
        gaps.append(gap)

    # gaps that no longer exist became covered by members
    for gid, g in existing.items():
        if gid not in live_ids and g.status != "covered" and g.window_end > now():
            g.status = "covered"
            g.resolution = g.resolution or "members now available"
            g.covered_by = g.covered_by or "members"
            r.store.put_gap(g)
            r.emit("gap_covered", gap_id=gid, by=g.covered_by)
    r.emit("coverage_computed", gaps=[{"id": g.id, "level": g.level, "score": g.risk_score,
                                        "window": f"{g.window_start:%a %H:%M}-{g.window_end:%H:%M}",
                                        "status": g.status} for g in gaps if g.level != Level.LOW])
    return gaps


def _gap_summary(g: Gap) -> dict:
    return {
        "id": g.id, "window_start": g.window_start.isoformat(), "window_end": g.window_end.isoformat(),
        "window": f"{g.window_start:%a %H:%M}-{g.window_end:%H:%M}", "district": g.district,
        "level": g.level.value, "risk_score": g.risk_score, "explanation": g.explanation, "status": g.status,
        "missing_roles": [x.value for x in g.inputs.missing_roles],
        "available_member_ids": g.inputs.available_member_ids,
        "expected_calls": g.inputs.expected_calls, "p_understaffed": g.inputs.p_understaffed,
        "hazard": g.inputs.hazard, "hazard_names": g.inputs.hazard_names, "severity": g.inputs.severity,
        "asked_member_ids": g.asked_member_ids, "asked_at": g.asked_at.isoformat() if g.asked_at else None,
        "next_check": g.next_check.isoformat() if g.next_check else None,
        "offers": [o.model_dump(mode="json") for o in g.offers], "chosen_peer": g.chosen_peer,
        "covered_by": g.covered_by, "resolution": g.resolution,
        "decision_sent_at": g.decision_sent_at.isoformat() if g.decision_sent_at else None,
    }


@tool
def compute_coverage(days: int = 7) -> list[dict]:
    """Recompute the coverage map for the next days and store every gap with its risk score.

    For each hour, checks whether the members who could respond can fill the minimum crew (exact matching).
    Hours group into shift windows. Each window is scored by the deterministic risk engine: expected calls
    from this department's own history, the probability that no qualified crew responds, active weather
    hazards, and call severity. Returns gaps at elevated level or above, highest risk first. Closer acts on
    high and critical gaps; elevated gaps are logged for the board.

    Args:
        days: horizon in days, default 7.
    """
    gaps = compute_gaps(days)
    return [_gap_summary(g) for g in gaps if g.status != "thin"] + \
        [{"note": "thin but coverable on paper, not actionable", **_gap_summary(g)}
         for g in gaps if g.status == "thin"]


@tool
def list_gaps(statuses: list[str] | None = None, min_level: str = "high") -> list[dict]:
    """List stored gaps at or above a level, optionally filtered by status, highest risk first.

    Args:
        statuses: subset of open, asking_members, members_declined, asking_neighbors, needs_chief,
                  covered, left_open, no_options. Default all.
        min_level: low, elevated, high, or critical. Default high.
    """
    order = [Level.LOW, Level.ELEVATED, Level.HIGH, Level.CRITICAL]
    floor = order.index(Level(min_level))
    out = []
    for g in rt().store.list_gaps(rt().dept_id, set(statuses) if statuses else None):
        if g.status == "thin" and not (statuses and "thin" in statuses):
            continue  # coverable on paper; there is nobody left to ask, so it is not actionable
        if order.index(g.level) >= floor and g.window_end > now():
            out.append(_gap_summary(g))
    return out


@tool
def get_gap(gap_id: str) -> dict:
    """Full detail of one gap including risk inputs, asks, offers, and status.

    Args:
        gap_id: the gap id.
    """
    return _gap_summary(rt().store.get_gap(rt().dept_id, gap_id))


@tool
def update_gap(gap_id: str, status: str, resolution: str = "", covered_by: str | None = None,
               next_check: str | None = None) -> dict:
    """Update a gap's workflow status.

    Args:
        gap_id: the gap id.
        status: open, asking_members, members_declined, asking_neighbors, needs_chief, covered, left_open,
                or no_options.
        resolution: one line on what happened.
        covered_by: member id, peer department id, or "members".
        next_check: ISO datetime when the agent should look at this gap again.
    """
    r = rt()
    g = r.store.get_gap(r.dept_id, gap_id)
    g.status = status  # type: ignore[assignment]
    if resolution:
        g.resolution = resolution
    if covered_by:
        g.covered_by = covered_by
    if next_check:
        g.next_check = parse_dt(next_check)
    r.store.put_gap(g)
    r.emit("gap_status", gap_id=gap_id, status=status, resolution=resolution, covered_by=covered_by)
    return _gap_summary(g)
