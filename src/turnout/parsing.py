"""Rule-based parser for member and chief SMS replies.

Handles the common cases deterministically so most replies never need a model call.
The Roll Call agent uses the model only when this returns intent "unknown" or low confidence.
"""

from __future__ import annotations

import re

from turnout.models import ParsedReply

YES = {"y", "yes", "yep", "yeah", "yup", "sure", "ok", "okay", "can do", "in", "i can", "i'm in",
       "im in", "count me in",
       "available", "good", "affirmative", "10-4", "104", "roger"}
NO = {"n", "no", "nope", "nah", "can't", "cant", "cannot", "out", "not available", "unavailable", "negative",
       "not this time", "busy", "working", "no can do"}

_TIME = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm|a|p)?", re.I)


def _hour(m: re.Match) -> int | None:
    h = int(m.group(1))
    mer = (m.group(3) or "").lower()
    if h > 24:
        return None
    if mer in ("pm", "p") and h < 12:
        h += 12
    if mer in ("am", "a") and h == 12:
        h = 0
    if not mer and 1 <= h <= 6:
        h += 12  # "till 2" means 2 pm in a daytime coverage context
    return h if 0 <= h <= 24 else None


def parse_reply(text: str) -> ParsedReply:
    raw = text.strip()
    t = raw.lower().strip().rstrip(".!")
    t = re.sub(r"\s+", " ", t)

    if t in {"stop", "unsubscribe", "quit", "cancel", "end"}:
        return ParsedReply(intent="stop")
    if t in {"start", "unstop", "resume"}:
        return ParsedReply(intent="start")
    if t in {"help", "info", "?"}:
        return ParsedReply(intent="help")
    if t in {"limits", "limit", "settings"}:
        return ParsedReply(intent="limits")
    if t in {"status", "board"}:
        return ParsedReply(intent="status")
    if t in {"gaps", "gap"}:
        return ParsedReply(intent="gaps")
    if t in {"undo"}:
        return ParsedReply(intent="decision", decision_choice="undo")
    if re.fullmatch(r"[123]|2[ab]", t):
        return ParsedReply(intent="decision", decision_choice=t)

    # partial windows: "till 2", "until noon", "morning only", "after 1", "from 1"
    if "noon" in t:
        if any(k in t for k in ("till", "til", "until", "before", "to ")):
            return ParsedReply(intent="partial", window_end_hour=12, confidence=0.95, note=raw)
        if "after" in t or "from" in t:
            return ParsedReply(intent="partial", window_start_hour=12, confidence=0.95, note=raw)
    if "morning" in t:
        return ParsedReply(intent="partial", window_end_hour=12, confidence=0.9, note=raw)
    if "afternoon" in t:
        return ParsedReply(intent="partial", window_start_hour=12, confidence=0.9, note=raw)
    m = re.search(r"(?:till|until|til|before|to)\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm|a|p)?)\b", t)
    if m:
        h = _hour(_TIME.match(m.group(1)))
        if h is not None:
            return ParsedReply(intent="partial", window_end_hour=h, confidence=0.9, note=raw)
    m = re.search(r"(?:after|from)\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm|a|p)?)\b", t)
    if m:
        h = _hour(_TIME.match(m.group(1)))
        if h is not None:
            return ParsedReply(intent="partial", window_start_hour=h, confidence=0.9, note=raw)

    words = t.split()
    if t in YES or (words and words[0] in YES and len(words) <= 3):
        return ParsedReply(intent="yes")
    if t in NO or (words and words[0] in NO and len(words) <= 4):
        return ParsedReply(intent="no")
    if any(p in t for p in ("not this week", "out of town", "on vacation", "away")):
        return ParsedReply(intent="no", confidence=0.85, note=raw)
    if any(p in t for p in ("i can", "count me", "put me")):
        return ParsedReply(intent="yes", confidence=0.85, note=raw)
    if any(p in t for p in ("can't", "cant", "won't", "wont", "unable")):
        return ParsedReply(intent="no", confidence=0.8, note=raw)
    return ParsedReply(intent="unknown", confidence=0.0, note=raw)
