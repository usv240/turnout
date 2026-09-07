"""House style, applied to text a model wrote.

`tools/check_copy.py` holds every file in this repository to one rule: no emoji, no em or en dashes.
It runs in CI on every push, and it never once looked at the text that actually reaches a person.

A good deal of what a chief or a volunteer reads is written at request time by a model: the reason a
window is at risk, a NERIS narrative, the line in a text message explaining a recommendation. Tally,
the sibling project, shipped two questions to its deployed service with em dashes in them, which is
the same code path and the same gap. A text message is the worse place for it, because an em dash
counts against a 160 character segment and some handsets render it as a box.

So model output passes through here on its way to a screen or a phone. Punctuation only: nothing is
truncated, reworded or dropped, because the point is a house style and not a filter.

The characters are built with `chr()` rather than written out. Putting them in a literal would make
ruff flag ambiguous Unicode, and would make `check_copy.py` fail the one file whose whole job is to
stop those characters reaching a person.
"""

from __future__ import annotations

import re
import unicodedata

# Dashes a model reaches for that this house does not use, mapped to what the sentence meant. An em
# dash is nearly always an aside, so it becomes a comma; the rest are ranges, so they become hyphens.
_DASHES = {
    chr(0x2014): ",",   # em dash
    chr(0x2015): ",",   # horizontal bar
    chr(0x2012): "-",   # figure dash
    chr(0x2013): "-",   # en dash
    chr(0x2212): "-",   # minus sign
}

_QUOTES = {
    chr(0x2018): "'", chr(0x2019): "'", chr(0x201A): "'", chr(0x201B): "'",
    chr(0x201C): '"', chr(0x201D): '"', chr(0x201E): '"', chr(0x201F): '"',
    chr(0x2032): "'", chr(0x2033): '"',
}

_ELLIPSIS = {chr(0x2026): "..."}

# Characters that look like a space, break like a space, and are not a space.
_SPACES = {chr(0x00A0): " ", chr(0x2007): " ", chr(0x2009): " ",
           chr(0x202F): " ", chr(0x200B): ""}

_MAP = {**_DASHES, **_QUOTES, **_ELLIPSIS, **_SPACES}


def _is_emoji(ch: str) -> bool:
    """Pictographs and symbols, without pulling in a dependency to decide.

    Deliberately narrow. Accented letters, currency and the degree sign are all ordinary text a
    provider might legitimately see, so only the symbol and pictograph blocks go.
    """
    # Category "So" alone is far too wide: it catches the degree sign, the copyright mark and the
    # currency symbols, all of which are ordinary text a provider might legitimately see. So this
    # goes by code point range and keeps the category check for lone surrogates only.
    if unicodedata.category(ch) == "Cs":
        return True
    code = ord(ch)
    return (
        0x1F000 <= code <= 0x1FAFF              # pictographs, emoticons, transport, flags
        or 0x2600 <= code <= 0x27BF             # misc symbols and dingbats
        or 0x2B00 <= code <= 0x2BFF             # misc symbols and arrows, the star among them
        or code in (0xFE0F, 0xFE0E, 0x20E3)     # variation selectors and the keycap combiner
    )


def plain(text: str) -> str:
    """One string of model output, in this house's punctuation.

    Idempotent, and safe on text that was already fine, which is most of it.
    """
    if not text:
        return text
    out = []
    for ch in text:
        if ch in _MAP:
            out.append(_MAP[ch])
        elif _is_emoji(ch):
            continue
        else:
            out.append(ch)
    # A dash replaced by a comma can leave " , " behind, and a stripped emoji can leave a double
    # space. Neither is worth showing a person.
    s = "".join(out)
    s = re.sub(r"\s+,", ",", s)
    s = re.sub(r",\s*,+", ",", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s.strip()


def plain_all(items: list[str]) -> list[str]:
    """The same, for a list, dropping anything that was only punctuation to begin with."""
    return [p for p in (plain(i) for i in items) if p]
