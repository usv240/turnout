"""SMS channel.

SimSmsChannel records outbound messages in the store and, when a scripted reply exists for the
recipient, queues an inbound reply after a simulated delay. The web app's Phones page reads the
same records, so judges see exactly what a real phone would show.

AwsSmsChannel sends through AWS End User Messaging (Pinpoint SMS v2). Inbound messages arrive
through SNS to a Lambda that calls `deliver_inbound`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from turnout.clock import Clock
from turnout.models import Message
from turnout.store import Store

InboundHandler = Callable[[str, str, datetime], None]  # (from_phone, body, at)


@dataclass
class ScriptedReply:
    body: str
    delay_min: int = 12


@dataclass
class PendingInbound:
    due: datetime
    from_phone: str
    body: str


class SimSmsChannel:
    def __init__(self, store: Store, clock: Clock) -> None:
        self.store = store
        self.clock = clock
        self.runtime: Any = None
        self.scripts: dict[str, dict[str, ScriptedReply]] = {}  # phone -> purpose -> reply
        self.pending: list[PendingInbound] = []
        self.inbound_handler: InboundHandler | None = None
        self.sent: list[Message] = field(default_factory=list) if False else []

    def script(self, phone: str, purpose: str, body: str, delay_min: int = 12) -> None:
        self.scripts.setdefault(phone, {})[purpose] = ScriptedReply(body, delay_min)

    def send(self, dept_id: str, to: str, body: str, purpose: str, member_id: str | None = None,
             held: bool = False) -> Message:
        msg = Message(dept_id=dept_id, at=self.clock.now(), to=to, member_id=member_id, direction="out",
                      body=body, purpose=purpose, held_for_quiet_hours=held)
        self.store.put_message(msg)
        self.sent.append(msg)
        if self.runtime is not None:
            self.runtime.emit("sms_out", to=to, member_id=member_id, body=body, purpose=purpose, held=held)
        reply = self.scripts.get(to, {}).get(purpose)
        if reply is not None:
            self.pending.append(PendingInbound(self.clock.now() + timedelta(minutes=reply.delay_min), to, reply.body))
        return msg

    def deliver_due(self) -> int:
        """Deliver scripted replies whose time has come. Returns count delivered."""
        now = self.clock.now()
        due = [p for p in self.pending if p.due <= now]
        self.pending = [p for p in self.pending if p.due > now]
        for p in sorted(due, key=lambda x: x.due):
            self.deliver_inbound(p.from_phone, p.body, p.due)
        return len(due)

    def deliver_inbound(self, from_phone: str, body: str, at: datetime | None = None) -> None:
        at = at or self.clock.now()
        found = self.store.get_member_by_phone(from_phone)
        dept_id = found[0].id if found else self._dept_for_chief(from_phone)
        member_id = found[1].id if found else None
        msg = Message(dept_id=dept_id or "", at=at, to=from_phone, member_id=member_id, direction="in",
                      body=body, purpose="reply")
        self.store.put_message(msg)
        if self.runtime is not None:
            self.runtime.emit("sms_in", frm=from_phone, member_id=member_id, body=body)
        if self.inbound_handler:
            self.inbound_handler(from_phone, body, at)

    def _dept_for_chief(self, phone: str) -> str | None:
        for d in self.store.list_departments():
            if d.chief_phone == phone or d.deputy_phone == phone:
                return d.id
        return None


class AwsSmsChannel:
    """AWS End User Messaging SMS. Requires an origination identity (toll-free number or 10DLC)."""

    def __init__(self, store: Store, clock: Clock, origination_identity: str, region: str) -> None:
        import boto3

        self.store = store
        self.clock = clock
        self.runtime: Any = None
        self.origination = origination_identity
        self.client = boto3.client("pinpoint-sms-voice-v2", region_name=region)
        self.inbound_handler: InboundHandler | None = None

    def send(self, dept_id: str, to: str, body: str, purpose: str, member_id: str | None = None,
             held: bool = False) -> Message:
        self.client.send_text_message(DestinationPhoneNumber=to, OriginationIdentity=self.origination,
                                      MessageBody=body, MessageType="TRANSACTIONAL")
        msg = Message(dept_id=dept_id, at=self.clock.now(), to=to, member_id=member_id, direction="out",
                      body=body, purpose=purpose, held_for_quiet_hours=held)
        self.store.put_message(msg)
        if self.runtime is not None:
            self.runtime.emit("sms_out", to=to, member_id=member_id, body=body, purpose=purpose, held=held)
        return msg

    def deliver_due(self) -> int:
        return 0

    def deliver_inbound(self, from_phone: str, body: str, at: datetime | None = None) -> None:
        at = at or self.clock.now()
        found = self.store.get_member_by_phone(from_phone)
        msg = Message(dept_id=found[0].id if found else "", at=at, to=from_phone,
                      member_id=found[1].id if found else None, direction="in", body=body, purpose="reply")
        self.store.put_message(msg)
        if self.runtime is not None:
            self.runtime.emit("sms_in", frm=from_phone, member_id=msg.member_id, body=body)
        if self.inbound_handler:
            self.inbound_handler(from_phone, body, at)
