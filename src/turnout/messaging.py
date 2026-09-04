"""Render SMS templates from messages.yaml. Length-checked. Never free-form."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml

_TEMPLATES: dict[str, str] | None = None
MEMBER_MAX = 160
CHIEF_MAX = 300


def templates() -> dict[str, str]:
    global _TEMPLATES
    if _TEMPLATES is None:
        path = Path(__file__).with_name("messages.yaml")
        _TEMPLATES = yaml.safe_load(path.read_text(encoding="utf-8"))
    return _TEMPLATES


def fmt_day(dt: datetime) -> str:
    return dt.strftime("%a")


def fmt_hour(dt: datetime) -> str:
    h = dt.hour
    suffix = "a" if h < 12 else "p"
    h12 = h % 12 or 12
    return f"{h12}{suffix}" if dt.minute == 0 else f"{h12}:{dt.minute:02d}{suffix}"


def render(key: str, **slots: object) -> str:
    text = templates()[key].format(**slots)
    limit = CHIEF_MAX if key in {"decision", "decision_multi", "decision_no_offer", "escalation", "status",
                                 "weekly", "options_header"} else MEMBER_MAX
    if len(text) > limit:
        raise ValueError(f"message '{key}' is {len(text)} chars, limit {limit}: {text!r}")
    return text


def role_word(role: str) -> str:
    return {"driver_operator": "driver", "firefighter": "firefighter", "emt": "EMT", "officer": "officer"}.get(role, role)
