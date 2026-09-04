"""Generate the three fictional departments, their members, twelve months of calls, and the demo week.

Deterministic (seeded). Run: python -m turnout.data.generate --out data/scenarios/demo_week.json

Design of the demo week (see DEMO_AND_VIDEO.md):
- Clock starts Wednesday 2026-09-09 06:30 (the day before the headline gap).
- Ice storm warning Thursday 2026-09-10 06:00 to 14:00.
- Millbrook Thursday 10:00-14:00 north: one firefighter available, no driver. Critical.
- Riverton has a daytime duty crew Thursday. Cedar Hollow is itself at high risk Thursday 10-14.
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from turnout.engine.risk import NATIONAL_DOW_PROFILE, NATIONAL_HOUR_PROFILE, NATIONAL_MONTH_PROFILE
from turnout.models import (
    AutoApproveRule,
    AvailabilityRecord,
    Call,
    Certification,
    Department,
    Member,
    ResponseStats,
    Role,
)

SEED = 20260910
DEMO_START = datetime(2026, 9, 9, 6, 30)  # Wednesday
GAP_DAY = datetime(2026, 9, 10)  # Thursday

FIRST = ["Dana", "Luis", "Marcy", "Tom", "Priya", "Dave", "Ellen", "Sam", "Rosa", "Hank", "Nia", "Ben", "Carla",
         "Omar", "Jill", "Ray", "Tess", "Walt", "Ivy", "Greg", "Lena", "Cal", "Ruth", "Ned", "Ana", "Kip",
         "Mona", "Zeke", "Faye", "Gus", "Ida", "Jo", "Kurt", "Liv", "Mel", "Nate", "Opal", "Pete", "Quinn", "Rae",
         "Sid", "Tia", "Uma", "Vic", "Wes", "Xan", "Yara", "Zed"]
LAST = ["Ortiz", "Reyes", "Kowalski", "Bright", "Nair", "Miller", "Shaw", "Okafor", "Delgado", "Booth", "Park",
        "Lund", "Vance", "Haddad", "Cole", "Ford", "Ames", "Grady", "Hale", "Ibsen", "Jett", "Knox", "Lowe", "Moss"]

CALL_TYPES = [("medical", 0.55, True), ("mvc", 0.12, True), ("fire_alarm", 0.10, False), ("structure_fire", 0.05, True),
              ("brush_fire", 0.05, False), ("service", 0.08, False), ("hazmat", 0.02, False), ("rescue", 0.03, True)]


def _phone(rng: random.Random, used: set[str]) -> str:
    while True:
        p = f"+1555{rng.randint(1000000, 9999999)}"
        if p not in used:
            used.add(p)
            return p


# Members of the same archetype are not clones. Two commuters both struggle on a weekday morning,
# but one of them has a boss who lets him leave. Without this, the roster page shows eight identical
# histories, which is not what a real department's year looks like.
JITTER = (0, 2, -2, 1, -1, 3, -3, 2, -1, 1, -2, 0, 3, -3)


def _profile(kind: str, index: int = 0) -> dict[str, tuple[int, int]]:
    """Response history (yes, no) per window type by member archetype, jittered per member.

    The jitter moves yes and no in opposite directions by at most three, so the archetype's total
    number of calls is preserved and only that member's willingness moves.
    """
    base = _archetype(kind)
    out = {}
    for k, (yes, no) in base.items():
        # sum of ordinals rather than hash(), which Python randomises per process.
        d = JITTER[(index * 5 + sum(ord(c) for c in k) % 5) % len(JITTER)]
        out[k] = (max(0, yes + d), max(0, no - d))
    return out


def _archetype(kind: str) -> dict[str, tuple[int, int]]:
    """Response history (yes, no) per window type by member archetype."""
    if kind == "retiree":
        return {"weekday_day": (28, 6), "weekday_evening": (20, 10), "weekday_night": (8, 14),
                "weekend_day": (22, 8), "weekend_evening": (14, 12), "weekend_night": (6, 16)}
    if kind == "commuter":
        return {"weekday_day": (3, 27), "weekday_evening": (22, 8), "weekday_night": (12, 12),
                "weekend_day": (20, 8), "weekend_evening": (18, 8), "weekend_night": (10, 12)}
    if kind == "shift":
        return {"weekday_day": (14, 16), "weekday_evening": (12, 16), "weekday_night": (18, 10),
                "weekend_day": (12, 14), "weekend_evening": (10, 14), "weekend_night": (16, 10)}
    return {"weekday_day": (10, 18), "weekday_evening": (16, 12), "weekday_night": (8, 16),
            "weekend_day": (16, 12), "weekend_evening": (14, 12), "weekend_night": (8, 14)}


def make_members(rng: random.Random, dept: Department, n: int, used: set[str], archetypes: list[str],
                 name_offset: int) -> list[Member]:
    members: list[Member] = []
    for i in range(n):
        kind = archetypes[i % len(archetypes)]
        roles = {Role.FIREFIGHTER}
        r = rng.random()
        if r < 0.35:
            roles.add(Role.DRIVER_OPERATOR)
        if rng.random() < 0.45:
            roles.add(Role.EMT)
        if i < 2:
            roles.add(Role.OFFICER)
        certs = [Certification(type="Firefighter I", expires=DEMO_START + timedelta(days=rng.randint(120, 700)))]
        if Role.EMT in roles:
            certs.append(Certification(type="EMT-B", expires=DEMO_START + timedelta(days=rng.randint(60, 700))))
        stats = {k: ResponseStats(yes=y, no=nn) for k, (y, nn) in _profile(kind, i).items()}
        qh = (22, 6) if kind != "shift" else (8, 15)
        name = f"{FIRST[(name_offset + i) % len(FIRST)]} {LAST[(name_offset * 3 + i) % len(LAST)]}"
        members.append(Member(id=f"{dept.id}-m{i + 1:02d}", dept_id=dept.id, name=name, phone=_phone(rng, used),
                              roles=sorted(roles), certs=certs, quiet_hours=qh, response_stats=stats))
    return members


def make_calls(rng: random.Random, dept: Department, members: list[Member], per_day: float,
               days: int = 365) -> list[Call]:
    calls: list[Call] = []
    start = DEMO_START - timedelta(days=days)
    for d in range(days):
        day = start + timedelta(days=d)
        lam = per_day * NATIONAL_DOW_PROFILE[day.weekday()] * NATIONAL_MONTH_PROFILE[day.month - 1]
        n = _poisson(rng, lam)
        for _ in range(n):
            hour = rng.choices(range(24), weights=NATIONAL_HOUR_PROFILE)[0]
            at = day.replace(hour=hour, minute=rng.randint(0, 59))
            ctype, _, crit = rng.choices(CALL_TYPES, weights=[w for _, w, _ in CALL_TYPES])[0]
            district = rng.choice(dept.districts)
            responders = [m.id for m in members if rng.random() < _resp_prob_at(m, at)]
            calls.append(Call(dept_id=dept.id, at=at, type=ctype, district=district,
                              duration_min=rng.randint(25, 120), responders=responders, time_critical=crit))
    return sorted(calls, key=lambda c: c.at)


def _resp_prob_at(m: Member, at: datetime) -> float:
    from turnout.engine.risk import response_probability, window_type

    s = m.response_stats.get(window_type(at), ResponseStats())
    return response_probability(s.yes, s.no)


def _poisson(rng: random.Random, lam: float) -> int:
    import math

    L = math.exp(-lam)
    k, p = 0, 1.0
    while True:
        p *= rng.random()
        if p <= L:
            return k
        k += 1


def build() -> dict:
    rng = random.Random(SEED)
    used: set[str] = set()

    millbrook = Department(
        id="millbrook", name="Millbrook Volunteer Fire Company", short_name="Millbrook VFC",
        districts=["north", "south"], chief_phone=_phone(rng, used), deputy_phone=_phone(rng, used),
        peers=["riverton", "cedar"], weather_zone="TXZ191", coordinates=(30.62, -98.41),
        peer_urls={"riverton": "http://127.0.0.1:9002", "cedar": "http://127.0.0.1:9003"},
    )
    riverton = Department(
        id="riverton", name="Riverton Fire and Rescue", short_name="Riverton F&R",
        districts=["central", "east"], chief_phone=_phone(rng, used), deputy_phone=_phone(rng, used),
        peers=["millbrook", "cedar"], weather_zone="TXZ191", coordinates=(30.60, -98.36),
        auto_approve=AutoApproveRule(enabled=True, max_delay_min=10, max_ledger_hours=8),
        peer_urls={"millbrook": "http://127.0.0.1:9001", "cedar": "http://127.0.0.1:9003"},
    )
    cedar = Department(
        id="cedar", name="Cedar Hollow Volunteer Fire Department", short_name="Cedar Hollow VFD",
        districts=["west"], chief_phone=_phone(rng, used), peers=["millbrook", "riverton"],
        weather_zone="TXZ191", coordinates=(30.70, -98.52),
        peer_urls={"millbrook": "http://127.0.0.1:9001", "riverton": "http://127.0.0.1:9002"},
    )

    m_members = make_members(rng, millbrook, 14, used, ["commuter", "commuter", "retiree", "shift", "commuter", "mixed"], 0)
    r_members = make_members(rng, riverton, 22, used, ["commuter", "retiree", "shift", "mixed"], 14)
    c_members = make_members(rng, cedar, 11, used, ["commuter", "commuter", "mixed", "retiree"], 36)

    # Make the Millbrook demo deterministic.
    # m03: retiree firefighter and EMT, no driver card, the one person available all Thursday.
    # m12: retiree driver and firefighter who did not answer the poll and says yes to a targeted ask.
    #      Saying yes closes the afternoon gap but cannot close the 10-14 gap (still one firefighter short).
    # m06, m09: commuter drivers who usually say yes on weekdays but decline this week. m06 is in quiet
    #      hours until 08:00 so the targeted ask is held, which the demo shows.
    # m11: EMT card expires Oct 30 for the Cert Clock demo.
    by_id = {m.id: m for m in m_members}
    by_id["millbrook-m03"].roles = [Role.EMT, Role.FIREFIGHTER]
    by_id["millbrook-m03"].response_stats = {k: ResponseStats(yes=y, no=n) for k, (y, n) in _profile("retiree").items()}
    by_id["millbrook-m12"].roles = sorted({Role.DRIVER_OPERATOR, Role.FIREFIGHTER})
    by_id["millbrook-m12"].response_stats = {k: ResponseStats(yes=y, no=n) for k, (y, n) in _profile("retiree").items()}
    for mid in ("millbrook-m06", "millbrook-m09"):
        by_id[mid].roles = sorted({Role.DRIVER_OPERATOR, Role.FIREFIGHTER})
        by_id[mid].response_stats["weekday_day"] = ResponseStats(yes=20, no=8)
    # m06 is the strongest weekday-daytime driver on the roster, so Closer asks him first, and he is
    # in quiet hours until 08:00, so the hook holds that message until then. Without the gap between
    # him and m09 the choice is a coin toss and the held message, which is the point of the hook,
    # may never appear on screen.
    by_id["millbrook-m06"].response_stats["weekday_day"] = ResponseStats(yes=28, no=2)
    by_id["millbrook-m06"].quiet_hours = (22, 8)  # in quiet hours until 08:00, so the ask is held
    # m14 is a driver who can only do mornings ("morning only"), which covers 06-10 and makes the
    # 10-14 block the single critical window rather than one of three.
    by_id["millbrook-m14"].roles = sorted({Role.DRIVER_OPERATOR, Role.FIREFIGHTER})
    for mid in ("millbrook-m01", "millbrook-m02", "millbrook-m04", "millbrook-m05", "millbrook-m07",
                "millbrook-m08", "millbrook-m10", "millbrook-m13"):
        by_id[mid].roles = sorted(set(by_id[mid].roles) - {Role.DRIVER_OPERATOR})
    by_id["millbrook-m11"].certs = [Certification(type="Firefighter I", expires=DEMO_START + timedelta(days=400)),
                                    Certification(type="EMT-B", expires=datetime(2026, 10, 30))]
    by_id["millbrook-m11"].roles = sorted({Role.FIREFIGHTER, Role.EMT})

    # Riverton: two daytime duty crew members (shift archetype with strong weekday_day stats) plus drivers.
    rb = {m.id: m for m in r_members}
    for mid in ("riverton-m03", "riverton-m04", "riverton-m07"):
        rb[mid].roles = sorted({Role.DRIVER_OPERATOR, Role.FIREFIGHTER, Role.EMT})
        rb[mid].response_stats["weekday_day"] = ResponseStats(yes=34, no=2)
    for mid in ("riverton-m05", "riverton-m08", "riverton-m10"):
        rb[mid].roles = sorted({Role.FIREFIGHTER})
        rb[mid].response_stats["weekday_day"] = ResponseStats(yes=30, no=4)

    # Cedar Hollow: thin on Thursday, everyone who is around is a commuter.
    for m in c_members:
        if Role.DRIVER_OPERATOR in m.roles:
            m.response_stats["weekday_day"] = ResponseStats(yes=2, no=26)

    calls = (make_calls(rng, millbrook, m_members, 2.0) + make_calls(rng, riverton, r_members, 3.0)
             + make_calls(rng, cedar, c_members, 1.0))

    # Scripted replies for Millbrook's Thursday poll (sent Wednesday 06:30) and targeted asks.
    # None means the member never answered the poll; those are the people Closer may ask directly.
    thu_poll = {
        "millbrook-m01": "N", "millbrook-m02": "N", "millbrook-m03": "Y", "millbrook-m04": "till 10",
        "millbrook-m05": None, "millbrook-m06": None, "millbrook-m07": "after 3", "millbrook-m08": "N",
        "millbrook-m09": None, "millbrook-m10": None, "millbrook-m11": "after 2", "millbrook-m12": None,
        "millbrook-m13": "depends on the kids, probably not", "millbrook-m14": "morning only",
    }
    asks = {"millbrook-m06": "N", "millbrook-m09": "sorry, can't, at the plant all day", "millbrook-m12": "Y"}

    # Seeded availability for Riverton and Cedar Hollow on Thursday (their own roll calls ran).
    seeded: list[AvailabilityRecord] = []
    thu_08, thu_17 = GAP_DAY.replace(hour=8), GAP_DAY.replace(hour=17)
    for mid in ("riverton-m03", "riverton-m04", "riverton-m07", "riverton-m05", "riverton-m08", "riverton-m10"):
        seeded.append(AvailabilityRecord(dept_id="riverton", member_id=mid, window_start=thu_08, window_end=thu_17,
                                         status="available", source="import", recorded_at=DEMO_START))
    for mid in ("cedar-m03",):
        seeded.append(AvailabilityRecord(dept_id="cedar", member_id=mid, window_start=thu_08, window_end=thu_17,
                                         status="available", source="import", recorded_at=DEMO_START))

    scenario = {
        "clock_start": DEMO_START.isoformat(),
        "weather_alerts": [{"zone": "TXZ191", "event": "Ice Storm Warning",
                            "start": GAP_DAY.replace(hour=6).isoformat(), "end": GAP_DAY.replace(hour=14).isoformat(),
                            "multiplier": 1.8}],
        "millbrook_poll_replies": thu_poll,
        "millbrook_ask_replies": asks,
        "chief_reply": "1",
        "incident": {"at": GAP_DAY.replace(hour=11, minute=52).isoformat(), "district": "north",
                     "voice_note": ("Riverton Engine 2 on scene 14 Elm, two vehicle MVC, one patient, "
                                    "extrication not needed, transported by Riverton ambulance, road closed "
                                    "forty minutes, cleared at twelve fifty. Four personnel."),
                     "type": "mvc"},
        "planted_gaps": [
            {"dept": "millbrook", "window": "Thu 10:00-14:00", "expected": "critical, closed by Riverton after chief approval"},
            {"dept": "millbrook", "window": "Thu 14:00-17:00", "expected": "high, closed by a member's yes to a targeted ask"},
            {"dept": "cedar", "window": "Thu 10:00-14:00", "expected": "high, Cedar Hollow declines Millbrook's request"},
        ],
    }

    return {
        "departments": [d.model_dump(mode="json") for d in (millbrook, riverton, cedar)],
        "members": [m.model_dump(mode="json") for m in (m_members + r_members + c_members)],
        "calls": [c.model_dump(mode="json") for c in calls],
        "availability": [a.model_dump(mode="json") for a in seeded],
        "scenario": scenario,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/scenarios/demo_week.json")
    args = ap.parse_args()
    blob = build()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(blob, indent=1), encoding="utf-8")
    print(f"wrote {out}: {len(blob['departments'])} departments, {len(blob['members'])} members, "
          f"{len(blob['calls'])} calls")


if __name__ == "__main__":
    main()
