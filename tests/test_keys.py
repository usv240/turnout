"""Minted keys, and every way one can fail.

The key is signed rather than stored, so these are the only checks standing between a forged key
and a 200. The sandbox is read-only over synthetic data, so nothing here is protecting much, and
that is exactly why the code has to be right: a security mechanism that is only decorative should
at least be correct decoration, or it teaches the wrong thing to anyone reading it.
"""

from __future__ import annotations

import time

from turnout import keys


def test_a_freshly_minted_key_is_valid():
    assert keys.valid(keys.mint()["key"])


def test_two_keys_minted_together_differ():
    """A nonce, so pressing the button twice visibly does something."""
    assert keys.mint()["key"] != keys.mint()["key"]


def test_the_key_says_when_it_expires():
    issued = keys.mint()
    assert issued["expires_epoch"] > time.time()
    assert issued["expires_in_seconds"] == keys.TTL_SECONDS


def test_an_expired_key_is_refused_and_says_so():
    old = keys.mint(ttl=-1)["key"]
    assert not keys.valid(old)
    assert "expired" in keys.why_invalid(old)


def test_a_tampered_expiry_does_not_extend_the_key():
    """The whole point of signing it: moving the expiry forward breaks the signature."""
    issued = keys.mint(ttl=-1)["key"]
    body = issued[len(keys.PREFIX) + 1:]
    payload, _, sig = body.rpartition("_")
    _, _, nonce = payload.partition(".")
    forged = f"{keys.PREFIX}_{int(time.time()) + 9999}.{nonce}_{sig}"
    assert not keys.valid(forged)
    assert "signature" in keys.why_invalid(forged)


def test_a_key_from_somewhere_else_is_refused():
    assert not keys.valid("to_9999999999.abcdef_0000000000000000")


def test_nonsense_is_refused_with_a_usable_reason():
    for junk in ("", None, "hello", "to_", "to_nope"):
        assert not keys.valid(junk)
    assert "Generate one" in keys.why_invalid("hello")


def test_the_signature_depends_on_the_secret(monkeypatch):
    """A deployment that sets its own secret does not accept this one's keys."""
    mine = keys.mint()["key"]
    monkeypatch.setenv(keys.SECRET_ENV, "a-different-deployment")
    assert not keys.valid(mine)
