"""Mutual aid signatures, without needing a server or credentials.

The over-the-wire versions of these live in test_a2a.py and are marked aws. These are the same rules
checked directly, so a broken signature check fails in a second rather than after two agents boot.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from turnout.a2a.identity import KEY_ENV, canonical, key_for, sign, verify
from turnout.models import CoverageRequest, Level, Role


def _req(**over) -> dict:
    base = CoverageRequest(
        request_id="sig-test", from_dept="millbrook",
        window_start=datetime(2026, 9, 10, 10), window_end=datetime(2026, 9, 10, 14),
        district="north", roles_needed=[Role.DRIVER_OPERATOR], risk_level=Level.CRITICAL,
        risk_explanation="short a driver", expires_at=datetime(2026, 9, 10, 9),
    ).model_dump(mode="json")
    base.update(over)
    return base


def _signed(as_dept: str = "millbrook", **over) -> dict:
    body = _req(**over)
    body["signature"] = ""
    body["signature"] = sign(as_dept, body)
    return body


def test_a_signature_from_the_right_department_verifies():
    v = verify(_signed(), "millbrook")
    assert v.ok
    assert v.signed_by == "millbrook"


def test_an_unsigned_request_is_refused():
    v = verify(_req(), "millbrook")
    assert not v.ok
    assert "unsigned" in v.reason


def test_signing_as_one_department_and_claiming_another_is_refused():
    """Cedar Hollow signs with its own key but puts Millbrook in from_dept."""
    body = _signed(as_dept="cedar")
    body["from_dept"] = "millbrook"
    v = verify(body, "millbrook")
    assert not v.ok
    assert "cedar" in v.reason


def test_editing_the_request_after_signing_is_refused():
    body = _signed()
    body["window_end"] = "2026-09-10T22:00:00"
    v = verify(body, "millbrook")
    assert not v.ok
    assert "does not match" in v.reason


def test_a_malformed_signature_is_refused():
    v = verify(_req(signature="not-a-signature"), "millbrook")
    assert not v.ok
    assert "malformed" in v.reason


def test_a_department_we_hold_no_agreement_with_is_refused(monkeypatch):
    """With a real keyring configured, a stranger is refused rather than trusted."""
    monkeypatch.setenv(KEY_ENV, "millbrook:mk,riverton:rk")
    body = _req(from_dept="stranger")
    body["signature"] = "v1:stranger:" + "0" * 64
    v = verify(body, "stranger")
    assert not v.ok
    assert "no mutual aid agreement" in v.reason


def test_a_configured_keyring_is_not_the_demo_keyring(monkeypatch):
    monkeypatch.setenv(KEY_ENV, "millbrook:mk,riverton:rk")
    body = _signed()
    v = verify(body, "millbrook")
    assert v.ok and not v.demo_key

    monkeypatch.delenv(KEY_ENV)
    assert key_for("millbrook")[1] is True


def test_signing_without_a_key_raises(monkeypatch):
    monkeypatch.setenv(KEY_ENV, "riverton:rk")
    with pytest.raises(ValueError, match="no mutual aid key"):
        sign("millbrook", _req())


def test_canonical_form_ignores_key_order_and_the_signature_itself():
    a = dict(_req())
    b = {k: a[k] for k in reversed(list(a))}
    assert canonical(a) == canonical(b)
    assert canonical(a) == canonical({**a, "signature": "v1:whoever:deadbeef"})
