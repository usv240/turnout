"""Getting a department in, from whatever the chief already has.

A volunteer chief does not have a roster in a database. She has a group text, a spreadsheet, or a
printed list on the wall. So the first screen takes a paste of any of those and works out the names,
the phone numbers and the roles, then shows her what it understood before saving anything.

Parsing runs as rules rather than a model, so it is instant, testable, and identical every time. The
lines it cannot read are reported rather than dropped, because a member missing from the roster is a
member the agent will never ask.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from turnout.models import MinCrew, Role

PHONE = re.compile(r"(\+?1[\s.\-]?)?\(?(\d{3})\)?[\s.\-]?(\d{3})[\s.\-]?(\d{4})\b")

ROLE_WORDS = {
    Role.DRIVER_OPERATOR: ["driver", "operator", "engineer", "chauffeur", "mpo", "dro"],
    Role.EMT: ["emt", "emt-b", "emtb", "medic", "paramedic", "ems", "aemt"],
    Role.OFFICER: ["chief", "captain", "lieutenant", "lt", "capt", "officer", "asst chief",
                   "assistant chief", "deputy"],
    Role.FIREFIGHTER: ["ff", "firefighter", "fire fighter", "interior", "exterior"],
}

# Words that look like a name but are not one.
NOT_NAMES = {"the", "and", "cell", "mobile", "home", "phone", "number", "roster", "member",
             "members", "name", "station", "dept", "department", "company", "crew", "list"}


class ParsedMember(BaseModel):
    name: str
    phone: str
    roles: list[Role] = Field(default_factory=list)
    source_line: str = ""


class ParsedRoster(BaseModel):
    members: list[ParsedMember] = Field(default_factory=list)
    unreadable: list[str] = Field(default_factory=list)
    """Lines that had something on them but no phone number. Reported, never silently dropped."""
    duplicates: list[str] = Field(default_factory=list)


def normalise_phone(raw: str) -> str | None:
    m = PHONE.search(raw)
    if not m:
        return None
    return f"+1{m.group(2)}{m.group(3)}{m.group(4)}"


def find_roles(text: str) -> list[Role]:
    low = " " + re.sub(r"[^a-z0-9 ]+", " ", text.lower()) + " "
    found: set[Role] = set()
    for role, words in ROLE_WORDS.items():
        for w in words:
            if f" {w} " in low:
                found.add(role)
                break
    # A chief, a driver operator and a lieutenant are all firefighters as well, and the minimum
    # crew is counted in firefighters. Leaving that off would make a department look short a
    # firefighter the moment it onboarded. Someone listed only as EMS is left as EMS.
    if found != {Role.EMT}:
        found.add(Role.FIREFIGHTER)
    return sorted(found)


def clean_name(text: str) -> str:
    """Whatever is left of a line once the phone number and the role words are taken out."""
    without_phone = PHONE.sub(" ", text)
    without_roles = without_phone
    for words in ROLE_WORDS.values():
        for w in words:
            without_roles = re.sub(rf"\b{re.escape(w)}\b", " ", without_roles, flags=re.I)
    cleaned = re.sub(r"[^A-Za-z'\-. ]+", " ", without_roles)
    tokens = [t for t in cleaned.split() if t.lower().strip(".'-") not in NOT_NAMES and len(t) > 1]
    return " ".join(t.capitalize() if t.islower() or t.isupper() else t for t in tokens[:3]).strip()


def parse_roster(text: str) -> ParsedRoster:
    """Read a pasted roster. Any format: a group text, a spreadsheet paste, a printed list."""
    out = ParsedRoster()
    seen: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip().strip("|,;")
        if not line or len(line) < 3:
            continue
        phone = normalise_phone(line)
        if phone is None:
            if re.search(r"[A-Za-z]{3,}", line):
                out.unreadable.append(line)
            continue
        name = clean_name(line)
        if not name:
            out.unreadable.append(line)
            continue
        if phone in seen:
            out.duplicates.append(f"{name} has the same number as {seen[phone]}")
            continue
        seen[phone] = name
        out.members.append(ParsedMember(name=name, phone=phone, roles=find_roles(line),
                                        source_line=line))
    return out


CREW_PRESETS: dict[str, dict] = {
    "engine": {
        "label": "Engine: one driver operator and two firefighters",
        "crew": MinCrew(fire={Role.DRIVER_OPERATOR: 1, Role.FIREFIGHTER: 2},
                        ems={Role.EMT: 1, Role.DRIVER_OPERATOR: 1}),
    },
    "ambulance": {
        "label": "Ambulance: one EMT and one driver",
        "crew": MinCrew(fire={Role.DRIVER_OPERATOR: 1, Role.FIREFIGHTER: 1},
                        ems={Role.EMT: 1, Role.DRIVER_OPERATOR: 1}),
    },
    "small": {
        "label": "Small department: one driver operator and one firefighter",
        "crew": MinCrew(fire={Role.DRIVER_OPERATOR: 1, Role.FIREFIGHTER: 1},
                        ems={Role.EMT: 1, Role.DRIVER_OPERATOR: 1}),
    },
}
