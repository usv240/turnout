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


# A genuine reply to a yes or no question is short. Above this, the rule heuristics stop being
# reading and start being guessing, so the message goes to the model instead. See the guard in
# parse_reply and evals/wild_eval.py for the measurement that set it.
MAX_RULE_WORDS = 10


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

    # Everything below here is a heuristic over the message body, and a heuristic over a long
    # message is a guess. A reply to "Reply Y or N, or a time like till 2" is short: the longest in
    # the entire test suite is four words.
    #
    # Measured against the first 500 messages of the UCI SMS Spam Collection, matching these
    # patterns anywhere in a long message misread 35 of them. "Goodmorning sleeping ga." read as
    # partial availability. "Your gonna have to pick up a $1 burger" read as yes. A member wrongly
    # read as available is a person on the board who is not coming, which is the one error this
    # system exists to prevent, so anything longer than a short reply goes to the model rather than
    # being guessed at here.
    if len(t.split()) > MAX_RULE_WORDS:
        return ParsedReply(intent="unknown", confidence=0.0, note=raw)

    # partial windows: "till 2", "until noon", "morning only", "after 1", "from 1"
    #
    # Whole words, not substrings. "Goodmorning sleeping ga." is a real message from the SMS corpus
    # and it contains "morning", which used to read as available until noon.
    if re.search(r"\bnoon\b", t):
        if any(k in t for k in ("till", "til", "until", "before", "to ")):
            return ParsedReply(intent="partial", window_end_hour=12, confidence=0.95, note=raw)
        if "after" in t or "from" in t:
            return ParsedReply(intent="partial", window_start_hour=12, confidence=0.95, note=raw)
    if re.search(r"\bmorning\b", t):
        return ParsedReply(intent="partial", window_end_hour=12, confidence=0.9, note=raw)
    if re.search(r"\bafternoon\b", t):
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
    if (any(p in t for p in ("not this week", "out of town", "on vacation"))
            or re.search(r"\baway\b", t)):
        return ParsedReply(intent="no", confidence=0.85, note=raw)
    # The word boundary rejects "cant" and "cannot"; the lookahead rejects "can't".
    # Without it, "I can't even move. Pain is killing me." read as yes, because it contains
    # "i can".
    if re.search(r"\bi can\b(?!')", t) or any(p in t for p in ("count me", "put me")):
        return ParsedReply(intent="yes", confidence=0.85, note=raw)
    if any(p in t for p in ("can't", "cant", "cannot", "won't", "wont", "unable")):
        return ParsedReply(intent="no", confidence=0.8, note=raw)
    return ParsedReply(intent="unknown", confidence=0.0, note=raw)
