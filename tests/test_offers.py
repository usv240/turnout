from datetime import datetime

from turnout.engine.offers import rank_offers, score_offer
from turnout.models import CoverageOffer, Role


def _offer(dept: str, can: bool, delay: int | None, reason: str = "") -> CoverageOffer:
    return CoverageOffer(request_id="r1", from_dept=dept, can_cover=can, estimated_delay_min=delay,
                         roles=[Role.DRIVER_OPERATOR, Role.FIREFIGHTER], ledger_delta_hours=4.0,
                         valid_until=datetime(2026, 9, 10, 18), reason_if_declined=reason)


def test_shorter_delay_scores_higher():
    a = score_offer(_offer("riverton", True, 9), 4, 0.2, 20)
    b = score_offer(_offer("cedar", True, 14), 4, 0.2, 20)
    assert a.score > b.score


def test_balanced_ledger_scores_higher():
    a = score_offer(_offer("riverton", True, 9), 0, 0.2, 20)
    b = score_offer(_offer("riverton", True, 9), 16, 0.2, 20)
    assert a.score > b.score


def test_peer_at_risk_penalized():
    a = score_offer(_offer("riverton", True, 9), 4, 0.1, 20)
    b = score_offer(_offer("riverton", True, 9), 4, 0.9, 20)
    assert a.score > b.score


def test_declined_offers_dropped_and_over_limit_sorted_last():
    d = score_offer(_offer("cedar", False, None, "own district at risk"), 0, 0.8, 20)
    slow = score_offer(_offer("far", True, 28), 0, 0.1, 20)
    fast = score_offer(_offer("riverton", True, 9), 4, 0.2, 20)
    ranked = rank_offers([d, slow, fast])
    assert [r.offer.from_dept for r in ranked] == ["riverton", "far"]
    assert ranked[1].over_max_delay
    assert "declined" in d.explanation
