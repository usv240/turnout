"""Ship the typefaces the design was drawn in, instead of naming them and hoping.

`--sans` has said Inter and `--mono` has said JetBrains Mono since the first commit, and neither
was ever loaded. Measured: a span set in Inter and a span set in a font that does not exist came
out the same width to two decimal places. So every visitor has been reading the fallback, and the
type scale, the weights and the letter-spacing were all tuned against a face nobody saw.

Self-hosted rather than linked. A third-party font request is a dependency the site does not need,
it leaks the reader's address to a CDN, and it is one more thing to be down. The latin subset of
each is small enough that the whole page stays under the performance budget.

Both faces are SIL Open Font License, which permits redistribution and requires the licence travel
with them. It is written next to the files.

    python fetch_fonts.py
"""

from __future__ import annotations

import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(r"C:\Hackathons\Agents for Humans Hackathon")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/120.0.0.0 Safari/537.36")

FACES = {
    "inter": ("https://fonts.googleapis.com/css2?family=Inter:wght@400..700&display=swap",
              "Inter", "400 700"),
    "jetbrains-mono": ("https://fonts.googleapis.com/css2?"
                       "family=JetBrains+Mono:wght@400..600&display=swap",
                       "JetBrains Mono", "400 600"),
}

# Only the latin block. The sites are in English and every other subset is weight nobody reads.
WANT = "/* latin */"


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main() -> int:
    faces = []
    for slug, (css_url, family, weights) in FACES.items():
        css = get(css_url).decode()
        block = None
        for part in css.split("/*"):
            if part.startswith(" latin */"):
                block = part
                break
        if not block:
            raise SystemExit(f"no latin subset found for {family}")
        url = re.search(r"url\((https://[^)]+\.woff2)\)", block).group(1)
        rng = re.search(r"unicode-range:\s*([^;]+);", block).group(1).strip()
        data = get(url)

        for proj in ("turnout", "tally"):
            out = ROOT / proj / "web" / "fonts"
            out.mkdir(parents=True, exist_ok=True)
            (out / f"{slug}.woff2").write_bytes(data)
        faces.append((family, weights, slug, rng, len(data)))
        print(f"  {family:<16} {len(data) / 1024:5.1f} KB")

    css = ["/* The typefaces this design was drawn in, served from here rather than a third party.",
           "",
           "   Both were named in the tokens from the start and neither was ever loaded, so every",
           "   visitor read the fallback and the type scale was tuned against a face nobody saw.",
           "",
           "   Self-hosted on purpose: no third-party request, nothing leaked to a font CDN, and one",
           "   less thing that can be down. Latin subset only, which is what these sites are written",
           "   in. Both faces are SIL Open Font License; see fonts/OFL.txt.",
           "",
           "   Regenerate with tools/fetch_fonts.py. */"]
    for family, weights, slug, rng, _ in faces:
        css += ["@font-face {",
                f"  font-family: '{family}';",
                "  font-style: normal;",
                f"  font-weight: {weights};",
                # swap, so text is readable immediately and reflows once rather than hiding.
                "  font-display: swap;",
                f"  src: url('fonts/{slug}.woff2') format('woff2');",
                f"  unicode-range: {rng};",
                "}"]
    body = "\n".join(css) + "\n"

    note = ("Inter and JetBrains Mono are licensed under the SIL Open Font License 1.1.\n"
            "Full text: https://openfontlicense.org\n\n"
            "Inter: https://github.com/rsms/inter\n"
            "JetBrains Mono: https://github.com/JetBrains/JetBrainsMono\n\n"
            "Only the latin subset is redistributed here. Regenerate with tools/fetch_fonts.py.\n")

    for proj in ("turnout", "tally"):
        (ROOT / proj / "web" / "fonts.css").write_text(body, encoding="utf-8")
        (ROOT / proj / "web" / "fonts" / "OFL.txt").write_text(note, encoding="utf-8")
        print(f"  {proj}/web/fonts.css and the licence written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
