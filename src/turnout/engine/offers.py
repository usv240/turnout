"""Offer evaluation for mutual aid. Deterministic and explainable.

score = 0.5 * delay_term + 0.3 * ledger_term + 0.2 * peer_risk_term
"""

from __future__ import annotations

from dataclasses import dataclass

from turnout.models import CoverageOffer

W_DELAY, W_LEDGER, W_PEER = 0.5, 0.3, 0.2


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


@dataclass
class ScoredOffer:
    offer: CoverageOffer
    score: float
    delay_term: float
    ledger_term: float
    peer_term: float
    over_max_delay: bool
    explanation: str


def score_offer(
    offer: CoverageOffer,
    ledger_balance_hours_after: float,
    peer_current_risk: float,
    max_delay_min: int,
) -> ScoredOffer:
    """ledger_balance_hours_after: our balance with this peer after accepting (positive means we owe)."""
    if not offer.can_cover:
        return ScoredOffer(offer, 0.0, 0.0, 0.0, 0.0, False, f"declined: {offer.reason_if_declined}")
    delay = offer.estimated_delay_min or 0
    d = clamp(1 - delay / 30)
    led = clamp(1 - abs(ledger_balance_hours_after) / 20)
    pr = clamp(1 - peer_current_risk)
    score = W_DELAY * d + W_LEDGER * led + W_PEER * pr
    over = delay > max_delay_min
    expl = f"{delay} min delay, balance after {ledger_balance_hours_after:+.0f} h, peer risk {peer_current_risk:.2f}"
    if over:
        expl += f", over your {max_delay_min} min limit"
    return ScoredOffer(offer, round(score, 3), round(d, 3), round(led, 3), round(pr, 3), over, expl)


def rank_offers(scored: list[ScoredOffer]) -> list[ScoredOffer]:
    accepted = [s for s in scored if s.offer.can_cover]
    return sorted(accepted, key=lambda s: (s.over_max_delay, -s.score))
