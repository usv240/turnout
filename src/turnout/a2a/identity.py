"""Proving which department is asking.

Millbrook's agent asks Riverton's agent to commit an apparatus and take on a ledger debt. Until this
module existed, Riverton took that on trust: anything that could reach the port could ask for a
crew, or confirm an offer in Millbrook's name and move hours onto Millbrook's side of the ledger.
Across an organizational boundary that is the whole question, and it is the one thing the rest of
this system is careful about everywhere else.

Departments do not roll for each other on a handshake. They sign a mutual aid agreement first, on
paper, naming the two parties. This mirrors that rather than inventing something cloud-shaped: the
two departments hold a key established when the agreement is signed, and every request crossing the
boundary carries an HMAC over its own contents. A request that is unsigned, signed by a department
we hold no agreement with, or signed by one department while claiming to come from another, is
refused with a reason rather than answered.

Stdlib only, deliberately. `hmac` and `hashlib` ship with Python, so this adds no dependency to a
deployed system a week before it is judged.

What this is not: it is not AgentCore Identity, and the architecture diagram still lists that as
designed rather than running. This is the smaller, honest version of the same idea.

Configuration
-------------
Set `TURNOUT_A2A_KEYS` to the agreements this department holds:

    TURNOUT_A2A_KEYS="millbrook:<key>,riverton:<key>,cedar:<key>"

With nothing set, the keyring is derived from a published constant so the local demo and the tests
run without setup. That is not a secret and is not pretending to be one: `Verdict.demo_key` is True
in that mode, the trace records it, and the network view says so on screen.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass

KEY_ENV = "TURNOUT_A2A_KEYS"
VERSION = "v1"

# Not a secret. It exists so that `python -m turnout.sim.runner` and the test suite have a working
# keyring with no configuration, and every verdict derived from it is labelled as such.
DEMO_SECRET = b"turnout-demo-mutual-aid-keyring"


@dataclass(frozen=True)
class Verdict:
    """The outcome of checking one request's signature."""

    ok: bool
    reason: str
    signed_by: str = ""
    demo_key: bool = False

    def as_event(self) -> dict:
        return {"verified": self.ok, "signed_by": self.signed_by,
                "reason": self.reason, "demo_key": self.demo_key}


def _configured_ring() -> dict[str, bytes]:
    raw = os.getenv(KEY_ENV, "").strip()
    if not raw:
        return {}
    ring: dict[str, bytes] = {}
    for pair in raw.split(","):
        dept, _, key = pair.partition(":")
        dept, key = dept.strip(), key.strip()
        if dept and key:
            ring[dept] = key.encode()
    return ring


def key_for(dept_id: str) -> tuple[bytes | None, bool]:
    """The key we share with one department, and whether it came from the demo keyring.

    Returns (None, False) when keys are configured but this department is not among them, which is
    the state that means "we have no mutual aid agreement with you".
    """
    ring = _configured_ring()
    if ring:
        return ring.get(dept_id), False
    return hmac.new(DEMO_SECRET, dept_id.encode(), hashlib.sha256).digest(), True


def canonical(payload: dict) -> bytes:
    """Stable bytes for a payload, with the signature itself left out.

    Sorted keys and no incidental whitespace, so that a dict rebuilt by Pydantic on the far side
    hashes to the same value as the one that was signed. `default=str` covers datetimes, which is
    what most of a coverage request is.
    """
    body = {k: v for k, v in payload.items() if k != "signature"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode()


def sign(dept_id: str, payload: dict) -> str:
    """Sign a payload as `dept_id`. Raises if we hold no key for that department."""
    key, _ = key_for(dept_id)
    if key is None:
        raise ValueError(f"no mutual aid key on file for {dept_id}")
    mac = hmac.new(key, canonical(payload), hashlib.sha256).hexdigest()
    return f"{VERSION}:{dept_id}:{mac}"


def verify(payload: dict, claimed_from: str) -> Verdict:
    """Check a payload's signature against the department it says it came from."""
    signature = str(payload.get("signature") or "")
    if not signature:
        return Verdict(False, "unsigned: no mutual aid signature on the request")

    parts = signature.split(":")
    if len(parts) != 3 or parts[0] != VERSION:
        return Verdict(False, f"malformed signature: {signature[:48]}")

    _, signer, mac = parts
    if signer != claimed_from:
        return Verdict(False, f"signed by {signer} but the request says it came from {claimed_from}")

    key, demo = key_for(signer)
    if key is None:
        return Verdict(False, f"no mutual aid agreement on file with {signer}")

    expected = hmac.new(key, canonical(payload), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, mac):
        return Verdict(False, f"signature does not match the contents of the request from {signer}")

    return Verdict(True, f"verified as {signer}", signed_by=signer, demo_key=demo)
