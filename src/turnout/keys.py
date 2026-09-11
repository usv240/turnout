"""Mint and check sandbox API keys, without storing any.

The developers page used to print one shared key and ask people to trust that the header did
something. That is a worse demonstration than it looks: a reader cannot tell whether the key is
checked at all, and the one thing they might want to do, call the thing themselves, needed them to
copy a constant out of a paragraph.

So the page mints a key instead. It is signed rather than stored: the expiry is put through HMAC
with a server secret, and checking it is recomputing that signature. No database, no cleanup, and a
key that was not issued here cannot be forged without the secret.

**This is a sandbox and the page says so.** Anyone can mint a key, so a key proves nothing about who
is calling. It exists so the authentication path is real and visible rather than described, and so
the shape matches a deployment where each department holds its own key. The data behind it is
synthetic and the whole demo resets.

Keys look like `to_<expiry>_<signature>` and last a day.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time

PREFIX = "to"
TTL_SECONDS = 24 * 60 * 60
SIG_CHARS = 16

# A real deployment sets this. The default keeps the demo self-contained, and it is not protecting
# anything: see the module docstring for why that is the honest position rather than a shortcut.
SECRET_ENV = "TURNOUT_KEY_SECRET"
DEFAULT_SECRET = b"turnout-sandbox-key-signing-2026"


def _secret() -> bytes:
    raw = os.environ.get(SECRET_ENV)
    return raw.encode() if raw else DEFAULT_SECRET


def _sign(payload: str) -> str:
    return hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()[:SIG_CHARS]


def mint(ttl: int = TTL_SECONDS) -> dict:
    """Issue a key that expires, and say when, so the caller does not have to guess."""
    expires = int(time.time()) + ttl
    # A nonce makes two keys minted in the same second differ, which is what a reader expects to
    # see when they press the button twice.
    nonce = secrets.token_hex(3)
    payload = f"{expires}.{nonce}"
    return {
        "key": f"{PREFIX}_{payload}_{_sign(payload)}",
        "expires_epoch": expires,
        "expires_in_seconds": ttl,
    }


def valid(key: str | None) -> bool:
    """True if this key was minted here and has not expired."""
    if not key or not key.startswith(PREFIX + "_"):
        return False
    # The payload joins expiry and nonce with a dot, and the signature is appended after the last
    # underscore. Splitting the whole key on underscores instead got the pieces wrong and rejected
    # every key this module had just issued.
    payload, _, sig = key[len(PREFIX) + 1:].rpartition("_")
    if not payload or not sig:
        return False
    if not hmac.compare_digest(sig, _sign(payload)):
        return False
    expires, _, _nonce = payload.partition(".")
    try:
        return int(expires) > time.time()
    except ValueError:
        return False


def why_invalid(key: str | None) -> str:
    """The reason, for an error a person has to act on rather than guess at."""
    if not key:
        return "no key given"
    if not key.startswith(PREFIX + "_"):
        return f"not a {PREFIX} key. Generate one on the API section of the landing page"
    payload, _, sig = key[len(PREFIX) + 1:].rpartition("_")
    if not payload or not sig:
        return "malformed key"
    if not hmac.compare_digest(sig, _sign(payload)):
        return "signature does not match, so this key was not issued by this deployment"
    return "expired. Generate a new one, they last a day"
