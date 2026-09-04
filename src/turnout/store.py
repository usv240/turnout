"""Repository for all records. Two implementations behind one interface.

MemoryStore: in-process, optional JSON persistence, used for local demo and tests.
DynamoStore: single-table DynamoDB, used on AWS. Same method names.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel

from turnout.models import (
    AvailabilityRecord,
    Call,
    Decision,
    Department,
    Gap,
    Incident,
    LedgerEntry,
    Member,
    Message,
)


class Store(Protocol):
    def get_department(self, dept_id: str) -> Department: ...
    def put_department(self, d: Department) -> None: ...
    def list_departments(self) -> list[Department]: ...
    def list_members(self, dept_id: str) -> list[Member]: ...
    def get_member(self, dept_id: str, member_id: str) -> Member: ...
    def get_member_by_phone(self, phone: str) -> tuple[Department, Member] | None: ...
    def put_member(self, m: Member) -> None: ...
    def put_availability(self, a: AvailabilityRecord) -> None: ...
    def list_availability(self, dept_id: str, start: datetime, end: datetime) -> list[AvailabilityRecord]: ...
    def list_calls(self, dept_id: str, since: datetime) -> list[Call]: ...
    def put_calls(self, calls: list[Call]) -> None: ...
    def put_gap(self, g: Gap) -> None: ...
    def get_gap(self, dept_id: str, gap_id: str) -> Gap: ...
    def list_gaps(self, dept_id: str, statuses: set[str] | None = None) -> list[Gap]: ...
    def put_ledger(self, e: LedgerEntry) -> None: ...
    def ledger_balance(self, dept_id: str, peer_id: str) -> float: ...
    def put_decision(self, d: Decision) -> None: ...
    def list_decisions(self, dept_id: str) -> list[Decision]: ...
    def put_message(self, m: Message) -> None: ...
    def list_messages(self, dept_id: str, phone: str | None = None) -> list[Message]: ...
    def put_incident(self, i: Incident) -> None: ...
    def get_incident(self, dept_id: str, incident_id: str) -> Incident: ...
    def list_incidents(self, dept_id: str) -> list[Incident]: ...


def _dump(obj: BaseModel) -> dict[str, Any]:
    return json.loads(obj.model_dump_json())


class MemoryStore:
    def __init__(self, persist_path: str | None = None) -> None:
        self.departments: dict[str, Department] = {}
        self.members: dict[str, dict[str, Member]] = {}
        self.availability: dict[str, list[AvailabilityRecord]] = {}
        self.calls: dict[str, list[Call]] = {}
        self.gaps: dict[str, dict[str, Gap]] = {}
        self.ledger: dict[str, list[LedgerEntry]] = {}
        self.decisions: dict[str, list[Decision]] = {}
        self.messages: dict[str, list[Message]] = {}
        self.incidents: dict[str, dict[str, Incident]] = {}
        self.persist_path = persist_path

    # Departments and members
    def get_department(self, dept_id: str) -> Department:
        return self.departments[dept_id]

    def put_department(self, d: Department) -> None:
        self.departments[d.id] = d
        self.members.setdefault(d.id, {})

    def list_departments(self) -> list[Department]:
        return list(self.departments.values())

    def list_members(self, dept_id: str) -> list[Member]:
        return list(self.members.get(dept_id, {}).values())

    def get_member(self, dept_id: str, member_id: str) -> Member:
        return self.members[dept_id][member_id]

    def get_member_by_phone(self, phone: str) -> tuple[Department, Member] | None:
        for d in self.departments.values():
            for m in self.members.get(d.id, {}).values():
                if m.phone == phone:
                    return d, m
        return None

    def put_member(self, m: Member) -> None:
        self.members.setdefault(m.dept_id, {})[m.id] = m

    # Availability
    def put_availability(self, a: AvailabilityRecord) -> None:
        lst = self.availability.setdefault(a.dept_id, [])
        # replace any record for same member and window
        lst[:] = [x for x in lst if not (x.member_id == a.member_id and x.window_start == a.window_start
                                         and x.window_end == a.window_end)]
        lst.append(a)

    def list_availability(self, dept_id: str, start: datetime, end: datetime) -> list[AvailabilityRecord]:
        return [a for a in self.availability.get(dept_id, []) if a.window_start < end and a.window_end > start]

    # Calls
    def list_calls(self, dept_id: str, since: datetime) -> list[Call]:
        return [c for c in self.calls.get(dept_id, []) if c.at >= since]

    def put_calls(self, calls: list[Call]) -> None:
        for c in calls:
            self.calls.setdefault(c.dept_id, []).append(c)

    # Gaps
    def put_gap(self, g: Gap) -> None:
        self.gaps.setdefault(g.dept_id, {})[g.id] = g

    def get_gap(self, dept_id: str, gap_id: str) -> Gap:
        return self.gaps[dept_id][gap_id]

    def list_gaps(self, dept_id: str, statuses: set[str] | None = None) -> list[Gap]:
        out = list(self.gaps.get(dept_id, {}).values())
        if statuses:
            out = [g for g in out if g.status in statuses]
        return sorted(out, key=lambda g: (-g.risk_score, g.window_start))

    # Ledger
    def put_ledger(self, e: LedgerEntry) -> None:
        self.ledger.setdefault(e.dept_id, []).append(e)

    def ledger_balance(self, dept_id: str, peer_id: str) -> float:
        """Positive means dept owes peer (received more than given)."""
        bal = 0.0
        for e in self.ledger.get(dept_id, []):
            if e.peer_id != peer_id:
                continue
            bal += e.hours if e.direction == "received" else -e.hours
        return bal

    # Decisions, messages, incidents
    def put_decision(self, d: Decision) -> None:
        self.decisions.setdefault(d.dept_id, []).append(d)

    def list_decisions(self, dept_id: str) -> list[Decision]:
        return list(self.decisions.get(dept_id, []))

    def put_message(self, m: Message) -> None:
        self.messages.setdefault(m.dept_id, []).append(m)

    def list_messages(self, dept_id: str, phone: str | None = None) -> list[Message]:
        msgs = self.messages.get(dept_id, [])
        if phone:
            msgs = [m for m in msgs if m.to == phone]
        return sorted(msgs, key=lambda m: m.at)

    def put_incident(self, i: Incident) -> None:
        self.incidents.setdefault(i.dept_id, {})[i.id] = i

    def get_incident(self, dept_id: str, incident_id: str) -> Incident:
        return self.incidents[dept_id][incident_id]

    def list_incidents(self, dept_id: str) -> list[Incident]:
        return sorted(self.incidents.get(dept_id, {}).values(), key=lambda i: i.at)

    # Persistence
    def save(self, path: str | None = None) -> None:
        p = Path(path or self.persist_path or "data/state.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        blob = {
            "departments": [_dump(d) for d in self.departments.values()],
            "members": [_dump(m) for dm in self.members.values() for m in dm.values()],
            "availability": [_dump(a) for lst in self.availability.values() for a in lst],
            "calls": [_dump(c) for lst in self.calls.values() for c in lst],
            "gaps": [_dump(g) for dg in self.gaps.values() for g in dg.values()],
            "ledger": [_dump(e) for lst in self.ledger.values() for e in lst],
            "decisions": [_dump(d) for lst in self.decisions.values() for d in lst],
            "messages": [_dump(m) for lst in self.messages.values() for m in lst],
            "incidents": [_dump(i) for di in self.incidents.values() for i in di.values()],
        }
        p.write_text(json.dumps(blob, indent=1), encoding="utf-8")

    @classmethod
    def load(cls, path: str) -> MemoryStore:
        blob = json.loads(Path(path).read_text(encoding="utf-8"))
        s = cls(persist_path=path)
        for d in blob["departments"]:
            s.put_department(Department.model_validate(d))
        for m in blob["members"]:
            s.put_member(Member.model_validate(m))
        for a in blob["availability"]:
            s.put_availability(AvailabilityRecord.model_validate(a))
        s.put_calls([Call.model_validate(c) for c in blob["calls"]])
        for g in blob["gaps"]:
            s.put_gap(Gap.model_validate(g))
        for e in blob["ledger"]:
            s.put_ledger(LedgerEntry.model_validate(e))
        for d in blob["decisions"]:
            s.put_decision(Decision.model_validate(d))
        for m in blob["messages"]:
            s.put_message(Message.model_validate(m))
        for i in blob["incidents"]:
            s.put_incident(Incident.model_validate(i))
        return s
