from __future__ import annotations

from strands import tool

from turnout.models import LedgerEntry
from turnout.tools.common import now, rt


@tool
def get_ledger(peer_id: str | None = None) -> list[dict]:
    """Mutual aid balances with peers. Positive balance means this department owes the peer hours.

    Args:
        peer_id: one peer, or all peers if omitted.
    """
    r = rt()
    d = r.store.get_department(r.dept_id)
    peers = [peer_id] if peer_id else d.peers
    return [{"peer": p, "balance_hours": r.store.ledger_balance(d.id, p)} for p in peers]


def record_ledger(dept_id: str, peer_id: str, direction: str, hours: float, request_id: str) -> None:
    r = rt()
    r.store.put_ledger(LedgerEntry(dept_id=dept_id, peer_id=peer_id, direction=direction, hours=hours,
                                   request_id=request_id, at=now()))
    r.emit("ledger", dept_id=dept_id, peer=peer_id, direction=direction, hours=hours)
