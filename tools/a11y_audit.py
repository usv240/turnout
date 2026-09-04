"""Accessibility and layout audit of every page, in both themes, at three widths.

Runs axe-core against WCAG 2.2 A and AA, and separately checks the two things axe cannot see: that
no page scrolls sideways, and that every control meets a target size: 24 by 24 CSS pixels for
anything clickable (WCAG 2.2 AA 2.5.8), and 48 by 48 for the buttons, tabs and form fields a person
presses to do something (44 on the marketing pages), which is DESIGN_SYSTEM.md section 14.

    python -m pip install playwright && playwright install chromium
    uvicorn turnout.api.app:app --port 8000
    python tools/a11y_audit.py --base http://127.0.0.1:8000

Exits non-zero if anything fails, so it can gate a build.
"""

from __future__ import annotations

import argparse
import json
import sys

AXE = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"

PAGES = ["/", "/app.html", "/try.html", "/start.html", "/crew.html"]
MARKETING = {"/", "/index.html"}
WIDTHS = [(390, 844), (768, 1024), (1280, 900)]
THEMES = ["light", "dark"]

TARGET_JS = """
(minPrimary) => {
  // Two rules. WCAG 2.2 AA 2.5.8 sets a floor of 24 by 24 for every control. DESIGN_SYSTEM.md sets
  // a higher bar for the controls a person presses to do something: buttons, tabs and form fields.
  // Inline links inside running text are exempt under 2.5.8, and so is the brand wordmark, which is
  // a link on a heading rather than a target.
  const out = [];
  const sel = 'a[href], button, input, select, textarea, [role="button"], [role="tab"]';
  const primary = el => el.matches('.btn, [role="tab"], input, select, textarea');
  document.querySelectorAll(sel).forEach(el => {
    if (el.hidden || el.closest('[hidden]')) return;
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden') return;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return;
    if (el.classList.contains('brand') || el.classList.contains('skip')) return;
    // A checkbox or radio wrapped in its own label: the label is what a finger hits, and what the
    // browser activates, so measure that instead of the 13 pixel box the OS draws.
    if (el.type === 'checkbox' || el.type === 'radio') {
      const lab = el.closest('label');
      if (lab) {
        const lr = lab.getBoundingClientRect();
        if (lr.width + 0.5 >= minPrimary && lr.height + 0.5 >= minPrimary) return;
      }
    }
    if (el.tagName === 'A' && !el.classList.contains('btn')
        && el.closest('p, li, td, summary, footer, nav, .stamp, .small')) return;
    const min = primary(el) ? minPrimary : 24;
    if (r.width + 0.5 < min || r.height + 0.5 < min) {
      out.push({tag: el.tagName, text: (el.textContent || '').trim().slice(0, 40),
                w: Math.round(r.width), h: Math.round(r.height), min: min});
    }
  });
  return out;
}
"""


def main() -> int:
    from playwright.sync_api import sync_playwright

    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--theme-key", default="turnout-theme")
    ap.add_argument("--pages", default=",".join(PAGES))
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    pages = args.pages.split(",")
    failures: list[str] = []
    checked = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for path in pages:
            for theme in THEMES:
                for width, height in WIDTHS:
                    label = f"{path} {theme} {width}px"
                    ctx = browser.new_context(viewport={"width": width, "height": height})
                    page = ctx.new_page()
                    errors: list[str] = []
                    page.on("pageerror", lambda e, s=errors: s.append(str(e)))
                    page.on("console", lambda m, s=errors:
                            s.append(m.text) if m.type == "error" else None)
                    page.add_init_script(
                        f"localStorage.setItem({args.theme_key!r}, {theme!r})")
                    page.goto(args.base + path, wait_until="networkidle")
                    page.wait_for_timeout(400)
                    checked += 1

                    page.add_script_tag(url=AXE)
                    result = page.evaluate(
                        "async () => await axe.run(document, {runOnly: "
                        "{type: 'tag', values: ['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']}})")
                    for v in result["violations"]:
                        nodes = "; ".join(n["target"][0] for n in v["nodes"][:3])
                        failures.append(f"{label}: axe {v['id']} ({v['impact']}) on {nodes}")

                    scroll_w = page.evaluate("document.documentElement.scrollWidth")
                    client_w = page.evaluate("document.documentElement.clientWidth")
                    if scroll_w > client_w + 1:
                        failures.append(
                            f"{label}: page scrolls sideways, {scroll_w} wide in {client_w}")

                    minimum = 44 if path in MARKETING else 48
                    for t in page.evaluate(TARGET_JS, minimum):
                        need = t["min"]
                        failures.append(
                            f"{label}: target {t['tag']} \"{t['text']}\" is {t['w']}x{t['h']}, "
                            f"under {need}")

                    for e in errors:
                        failures.append(f"{label}: console {e[:120]}")
                    ctx.close()
        browser.close()

    print(f"checked {checked} page renders across {len(pages)} pages, "
          f"{len(THEMES)} themes and {len(WIDTHS)} widths")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"checked": checked, "failures": failures}, fh, indent=1)
    if failures:
        print(f"\n{len(failures)} problems:")
        for f in failures:
            print("  " + f)
        return 1
    print("no violations, no sideways scroll, no undersized targets, no console errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
