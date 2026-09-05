"""Domain models. Pydantic so every agent output and every stored record is typed.

Naming follows the fire service: roll call, watch, gap, second due, mutual aid, ledger.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class Role(StrEnum):
    FIREFIGHTER = "firefighter"
    DRIVER_OPERATOR = "driver_operator"
    EMT = "emt"
    OFFICER = "officer"


class Level(StrEnum):
    LOW = "low"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"


class Availability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class Certification(BaseModel):
    type: str
    expires: datetime


class ResponseStats(BaseModel):
    """Per member, per window type. Counts of responded yes / no to actual calls or asks."""

    yes: int = 0
    no: int = 0


class Member(BaseModel):
    id: str
    dept_id: str
    name: str
    phone: str
    roles: list[Role]
    certs: list[Certification] = Field(default_factory=list)
    quiet_hours: tuple[int, int] = (22, 6)  # local hours, start and end
    opted_out: bool = False
    asks_this_week: int = 0
    # window_type -> stats. Window types: weekday_day, weekday_evening, weekday_night,
    # weekend_day, weekend_evening, weekend_night
    response_stats: dict[str, ResponseStats] = Field(default_factory=dict)


class MinCrew(BaseModel):
    """Minimum qualified crew per apparatus type."""

    fire: dict[Role, int] = Field(default_factory=lambda: {Role.DRIVER_OPERATOR: 1, Role.FIREFIGHTER: 2})
    ems: dict[Role, int] = Field(default_factory=lambda: {Role.EMT: 1, Role.DRIVER_OPERATOR: 1})


class AutoApproveRule(BaseModel):
    enabled: bool = False
    max_delay_min: int = 10
    max_ledger_hours: int = 6


class Department(BaseModel):
    id: str
    name: str
    short_name: str
    tz: str = "America/Chicago"
    districts: list[str]
    min_crew: MinCrew = Field(default_factory=MinCrew)
    peers: list[str] = Field(default_factory=list)  # dept ids
    peer_urls: dict[str, str] = Field(default_factory=dict)  # dept id -> A2A base url
    chief_phone: str
    deputy_phone: str | None = None
    weekly_ask_limit: int = 2
    auto_approve: AutoApproveRule = Field(default_factory=AutoApproveRule)
    weather_zone: str = "TXZ000"
    max_offer_delay_min: int = 20
    coordinates: tuple[float, float] = (0.0, 0.0)  # for the network view, fictional


class AvailabilityRecord(BaseModel):
    dept_id: str
    member_id: str
    window_start: datetime
    window_end: datetime
    status: Availability
    source: Literal["poll", "ask", "swap", "manual", "import"] = "poll"
    note: str = ""
    recorded_at: datetime


class Call(BaseModel):
    dept_id: str
    at: datetime
    type: str
    district: str
    duration_min: int
    responders: list[str]
    time_critical: bool


class WeatherAlert(BaseModel):
    event: str  # e.g. "Ice Storm Warning"
    start: datetime
    end: datetime
    multiplier: float


class RiskInputs(BaseModel):
    expected_calls: float
    p_understaffed: float
    hazard: float
    hazard_names: list[str]
    severity: float
    missing_roles: list[Role]
    available_member_ids: list[str]
    history_days: int
    ran_in: str = "local"
    """Where the matching and probability executed: agentcore_code_interpreter, local, local_cached,
    or local_fallback when AgentCore was unreachable. Shown on the gap card, because a claim about
    where code ran is only worth making if it can be checked."""
    fallback_reason: str = ""
    """The error that sent it local, when one did. Shown on the card and put in the trace, so a
    fallback is a fact on the screen rather than a quiet substitution."""


GapStatus = Literal["open", "asking_members", "members_declined", "asking_neighbors", "needs_chief",
                    "covered", "left_open", "no_options", "thin"]
"""thin: the crew can be formed on paper, but the odds of it actually turning out are poor. Shown on the
board and in the weekly summary, never acted on, because there is nobody left to ask."""


class CoverageOffer(BaseModel):
    request_id: str
    from_dept: str
    can_cover: bool
    estimated_delay_min: int | None = None
    roles: list[Role] = Field(default_factory=list)
    conditions: str = ""
    ledger_delta_hours: float = 0.0
    valid_until: datetime | None = None
    reason_if_declined: str = ""
    peer_current_risk: float = 0.0
    auto_approved: bool = False


class Gap(BaseModel):
    id: str
    dept_id: str
    window_start: datetime
    window_end: datetime
    district: str
    apparatus: Literal["fire", "ems"] = "fire"
    inputs: RiskInputs
    risk_score: float
    level: Level
    explanation: str
    status: GapStatus = "open"
    resolution: str = ""
    covered_by: str | None = None  # member id or peer dept id
    asked_member_ids: list[str] = Field(default_factory=list)
    asked_for_roles: list[Role] = Field(default_factory=list)
    asked_at: datetime | None = None
    next_check: datetime | None = None
    request_id: str | None = None
    offers: list[CoverageOffer] = Field(default_factory=list)
    chosen_peer: str | None = None
    decision_sent_at: datetime | None = None
    escalated: bool = False
    confirmed_at: datetime | None = None


class CoverageRequest(BaseModel):
    request_id: str
    from_dept: str
    window_start: datetime
    window_end: datetime
    district: str
    roles_needed: list[Role]
    risk_level: Level
    risk_explanation: str
    expires_at: datetime


class CoverageConfirm(BaseModel):
    request_id: str
    confirmed_by: str
    confirmed_at: datetime


class LedgerEntry(BaseModel):
    dept_id: str
    peer_id: str
    direction: Literal["given", "received"]
    hours: float
    request_id: str
    at: datetime


class Decision(BaseModel):
    dept_id: str
    gap_id: str
    at: datetime
    message_sent: str
    reply: str = ""
    action_taken: str = ""
    trace_id: str = ""


class Message(BaseModel):
    dept_id: str
    at: datetime
    to: str  # phone
    member_id: str | None
    direction: Literal["out", "in"]
    body: str
    purpose: str  # poll, ask, swap, decision, cert, status, summary, ack, system
    held_for_quiet_hours: bool = False


class ParsedReply(BaseModel):
    """Structured reading of a member's SMS reply."""

    intent: Literal["yes", "no", "partial", "stop", "help", "limits", "start", "status", "gaps", "decision", "unknown"]
    window_start_hour: int | None = None
    window_end_hour: int | None = None
    decision_choice: str | None = None  # "1", "2", "3", "2a", "2b", "undo"
    confidence: float = 1.0
    note: str = ""


class NerisDraft(BaseModel):
    incident_types: list[str] = Field(default_factory=list, max_length=3)
    location: str = ""
    district: str = ""
    dispatch_time: datetime | None = None
    arrival_time: datetime | None = None
    clear_time: datetime | None = None
    units: list[str] = Field(default_factory=list)
    personnel_count: int | None = None
    actions_taken: list[str] = Field(default_factory=list)
    casualties: int = 0
    narrative: str = ""
    uncertain_fields: list[str] = Field(default_factory=list)


class Incident(BaseModel):
    id: str
    dept_id: str
    at: datetime
    audio_key: str | None = None
    transcript: str = ""
    draft: NerisDraft | None = None
    status: Literal["draft", "reviewed", "submitted"] = "draft"
