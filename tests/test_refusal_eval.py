"""The refusal eval is the headline number on docs/EVAL.md, so it runs in CI like anything else.

A published number that nobody reruns is an assertion. This makes it a measurement: if a refusal
stops working, or if the system starts refusing something legitimate, the build fails rather than
the page quietly becoming untrue.
"""

from __future__ import annotations

from evals import refusal_eval


def _run() -> refusal_eval.Result:
    r = refusal_eval.Result()
    for check in (refusal_eval.check_identity, refusal_eval.check_contact_policy,
                  refusal_eval.check_quiet_hours, refusal_eval.check_scoring_endpoint,
                  refusal_eval.check_interrupt_budget):
        check(r)
    return r


def test_every_adversarial_case_is_refused():
    failed = [c.name for c in _run().adversarial if not c.passed]
    assert not failed, f"these were not refused: {failed}"


def test_nothing_legitimate_is_refused():
    """The control. A false refusal is worse than the thing it was guarding against."""
    failed = [c.name for c in _run().legitimate if not c.passed]
    assert not failed, f"these were wrongly refused: {failed}"


def test_the_published_number_matches_what_the_eval_measures():
    """docs/EVAL.md leads with a count. It has to be the count this produces."""
    import pathlib
    import re

    r = _run()
    claim = f"{len(r.adversarial)} of {len(r.adversarial)} adversarial cases refused"
    page = pathlib.Path("docs/EVAL.md").read_text(encoding="utf-8")
    assert claim in page, f"EVAL.md does not say {claim!r}. Rerun python -m evals.refusal_eval --out docs/EVAL.md"
    assert re.search(rf"{len(r.legitimate)} legitimate cases", page)


def test_both_sides_are_actually_populated():
    """A one-sided eval proves nothing, so guard against the controls being deleted."""
    r = _run()
    assert len(r.adversarial) >= 10
    assert len(r.legitimate) >= 5
