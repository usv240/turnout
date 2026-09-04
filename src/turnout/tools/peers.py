"""Neighbor's tools: talk to peer departments. Local peers run in-process; AWS peers are A2A clients.

Both implement `ask(req) -> CoverageOffer` and `confirm(conf, req) -> dict`.
"""

from __future__ import annotations

import json
import uuid
from datetime import timedelta

from strands import tool

from turnout import runtime
from turnout.a2a.client import extract_json
from turnout.engine.offers import rank_offers, score_offer
from turnout.models import CoverageConfirm, CoverageOffer, CoverageRequest
from turnout.tools.common import dept, now, rt
from turnout.tools.coverage import _gap_summary


class LocalPeer:
    """A peer department in the same process, used by the single-command local demo.

    Answers with the peer's own department id set, so the peer reasons about its own coverage using
    its own data. The A2A path is the real one; this keeps the demo to one command.
    """

    def __init__(self, dept_id: str) -> None:
        self.dept_id = dept_id

    def _as_peer(self, fn):
        r = runtime.get()
        me = r.dept_id
        r.dept_id = self.dept_id
        try:
            return fn(r)
        finally:
            r.dept_id = me

    def ask(self, req: CoverageRequest) -> CoverageOffer:
        from turnout.agents.peer_service import evaluate_request

        return self._as_peer(lambda r: evaluate_request(req, rt=r))

    def confirm(self, conf: CoverageConfirm, req: CoverageRequest) -> dict:
        from turnout.agents.peer_service import apply_confirm

        return self._as_peer(lambda r: apply_confirm(conf, req, rt=r))


class A2APeer:
    """A peer department reached over the Agent-to-Agent protocol."""

    def __init__(self, dept_id: str, base_url: str, timeout: float = 60.0) -> None:
        self.dept_id = dept_id
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _send(self, text: str) -> str:
        from turnout.a2a.client import send_text

        return send_text(self.base_url, text, timeout=self.timeout)

    def ask(self, req: CoverageRequest) -> CoverageOffer:
        out = self._send("COVERAGE_REQUEST " + req.model_dump_json())
        return CoverageOffer.model_validate_json(extract_json(out))

    def confirm(self, conf: CoverageConfirm, req: CoverageRequest) -> dict:
        payload = {"confirm": conf.model_dump(mode="json"), "request": req.model_dump(mode="json")}
        out = self._send("COVERAGE_CONFIRM " + json.dumps(payload))
        return json.loads(extract_json(out))


def _peer(peer_id: str):
    r = rt()
    if peer_id in r.peers:
        return r.peers[peer_id]
    d = dept()
    url = d.peer_urls.get(peer_id)
    if url and r.use_a2a:
        p = A2APeer(peer_id, url)
    else:
        p = LocalPeer(peer_id)
    r.peers[peer_id] = p
    return p


@tool
def request_coverage_from_peers(gap_id: str) -> dict:
    """Ask every mutual aid peer to cover a gap, over the Agent-to-Agent protocol, and rank their offers.

    Scores each offer by response delay, the ledger balance after accepting, and the peer's own risk in that
    window. Stores the offers on the gap and sets its status to needs_chief when there is at least one offer,
    or no_options when there is none. Never confirms anything.

    Args:
        gap_id: the gap id.
    """
    r = rt()
    d = dept()
    g = r.store.get_gap(d.id, gap_id)
    req = CoverageRequest(request_id=g.request_id or f"req-{uuid.uuid4().hex[:8]}", from_dept=d.id,
                          window_start=g.window_start, window_end=g.window_end, district=g.district,
                          roles_needed=list(g.inputs.missing_roles) or list(d.min_crew.fire),
                          risk_level=g.level, risk_explanation=g.explanation,
                          expires_at=min(g.window_start, now() + timedelta(hours=9)))
    g.request_id = req.request_id
    g.status = "asking_neighbors"
    r.store.put_gap(g)
    r.emit("a2a_request", request_id=req.request_id, peers=d.peers, window=f"{g.window_start:%a %H:%M}-{g.window_end:%H:%M}")

    scored = []
    offers: list[CoverageOffer] = []
    hours = (g.window_end - g.window_start).total_seconds() / 3600
    for peer_id in d.peers:
        try:
            offer = _peer(peer_id).ask(req)
        except Exception as e:  # a peer that is down or unintelligible is a decline with a reason
            r.emit("a2a_error", peer=peer_id, error=f"{type(e).__name__}: {e}"[:300])
            offer = CoverageOffer(request_id=req.request_id, from_dept=peer_id, can_cover=False,
                                  reason_if_declined=f"no usable answer from {peer_id}")
        offers.append(offer)
        balance_after = r.store.ledger_balance(d.id, peer_id) + (hours if offer.can_cover else 0)
        scored.append(score_offer(offer, balance_after, offer.peer_current_risk, d.max_offer_delay_min))
    ranked = rank_offers(scored)
    g.offers = [s.offer for s in ranked] + [o for o in offers if not o.can_cover]
    if ranked:
        g.chosen_peer = ranked[0].offer.from_dept
        g.status = "needs_chief"
    else:
        g.status = "no_options"
    r.store.put_gap(g)
    r.emit("gap_status", gap_id=gap_id, status=g.status, chosen=g.chosen_peer)
    return {
        "gap": _gap_summary(g),
        "ranked": [{"peer": s.offer.from_dept, "score": s.score, "delay_min": s.offer.estimated_delay_min,
                    "ledger_delta_hours": s.offer.ledger_delta_hours, "explanation": s.explanation,
                    "over_max_delay": s.over_max_delay} for s in ranked],
        "declined": [{"peer": o.from_dept, "reason": o.reason_if_declined} for o in offers if not o.can_cover],
    }


def confirm_with_peer(gap_id: str, peer_id: str) -> dict:
    """Confirm the chosen offer with the peer. Called by Chief Gate after the chief approves."""
    r = rt()
    d = dept()
    g = r.store.get_gap(d.id, gap_id)
    req = CoverageRequest(request_id=g.request_id or "", from_dept=d.id, window_start=g.window_start,
                          window_end=g.window_end, district=g.district,
                          roles_needed=list(g.inputs.missing_roles) or list(d.min_crew.fire),
                          risk_level=g.level, risk_explanation=g.explanation, expires_at=g.window_start)
    conf = CoverageConfirm(request_id=req.request_id, confirmed_by=d.id, confirmed_at=now())
    result = _peer(peer_id).confirm(conf, req)
    if result.get("accepted"):
        from turnout.tools.ledger import record_ledger

        hours = round((g.window_end - g.window_start).total_seconds() / 3600, 1)
        record_ledger(d.id, peer_id, "received", hours, req.request_id)
        g.status = "covered"
        g.covered_by = peer_id
        g.confirmed_at = now()
        g.resolution = str(result.get("note", "")).strip()
        r.store.put_gap(g)
        r.emit("gap_covered", gap_id=gap_id, by=peer_id, auto_approved=result.get("auto_approved"))
    return result
