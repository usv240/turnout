"""House style, checked rather than remembered.

Two rules the whole project keeps: no emoji anywhere, and no em or en dashes. A dash that renders as
a hyphen on one screen and a long rule on another is not worth the ambiguity, and emoji in a product
that reads text aloud to someone with their hands full is noise. The geometric shapes used as
non-colour status indicators are allowed, because colour alone is not an accessible signal.

    python tools/check_copy.py

Exits non-zero on any hit, so it can gate a build.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

DASHES = "\u2014\u2013"
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F]")
SHAPES = set("\u2b23\u25c6\u25b2\u25cf\u25a0")  # the status glyphs, deliberate
SUFFIXES = {".py", ".js", ".css", ".html", ".md", ".json", ".yaml", ".yml", ".sh", ".svg", ".txt"}
SKIP = {".git", "__pycache__", ".venv", "node_modules", ".ruff_cache", ".pytest_cache"}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    hits: list[str] = []
    for path in root.rglob("*"):
        if path.suffix.lower() not in SUFFIXES or not path.is_file():
            continue
        if any(part in SKIP for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            for ch in line:
                if ch in DASHES:
                    hits.append(f"{path.relative_to(root)}:{i}: dash U+{ord(ch):04X}")
                elif EMOJI.match(ch) and ch not in SHAPES:
                    hits.append(f"{path.relative_to(root)}:{i}: emoji U+{ord(ch):04X}")
    if hits:
        print(f"{len(hits)} problems:")
        for h in hits[:80]:
            print("  " + h)
        return 1
    print("copy is clean: no emoji, no em or en dashes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
