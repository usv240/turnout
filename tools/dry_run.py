"""Walk the whole product the way a judge would, and report anything broken.

The accessibility audit checks how a page is built. This checks whether it works: every page loads,
every step runs, every tab fills, every image arrives, every request succeeds, and nothing throws.
Those are different questions, and a demo can pass the first and fail the second.

Run before recording. If this is not clean, the recording is not worth making.

    python dry_run.py turnout https://...
"""

from __future__ import annotations

import sys
import time

from playwright.sync_api import sync_playwright

PLANS = {
    "turnout": {
        "pages": ["/", "/app.html", "/try.html", "/start.html", "/crew.html"],
        "tabs": ["tab-board", "tab-phones", "tab-network", "tab-trace", "tab-incident"],
        "theme_key": "turnout-theme",
    },
    "tally": {
        "pages": ["/", "/app.html", "/try.html", "/start.html", "/sponsor.html"],
        "tabs": ["tab-today", "tab-children", "tab-evening", "tab-month", "tab-trace"],
        "theme_key": "tally-theme",
    },
}


def main() -> int:
    project, base = sys.argv[1], sys.argv[2]
    plan = PLANS[project]
    problems: list[str] = []
    notes: list[str] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1600, "height": 900})
        pg = ctx.new_page()
        pg.add_init_script(f"localStorage.setItem({plan['theme_key']!r}, 'light')")

        pg.on("pageerror", lambda e: problems.append(f"uncaught: {e}"))
        pg.on("console", lambda m: problems.append(f"console: {m.text[:120]}")
              if m.type == "error" else None)
        pg.on("requestfailed", lambda r: problems.append(
            f"request failed: {r.url.split('/')[-1]} {r.failure}"))
        pg.on("response", lambda r: problems.append(
            f"HTTP {r.status} on {r.url.replace(base, '')}")
            if r.status >= 400 and "/api/keys" not in r.url else None)

        print("  0. resetting, so this is a real run from the start")
        pg.request.post(base + "/api/reset")

        print("  1. every page loads")
        for path in plan["pages"]:
            pg.goto(base + path, wait_until="networkidle")
            pg.wait_for_timeout(500)
            title = pg.title()
            if not title or "error" in title.lower():
                problems.append(f"{path}: title is {title!r}")
            broken = pg.eval_on_selector_all(
                "img", "els => els.filter(e => !e.complete || e.naturalWidth === 0)"
                       ".map(e => e.getAttribute('src'))")
            for b in broken:
                problems.append(f"{path}: image did not load, {b}")
            print(f"     {path:<16} {title[:52]}")

        print("  2. minting a key and calling every endpoint")
        pg.goto(base + "/#api", wait_until="networkidle")
        pg.click("#api-try button.primary")
        pg.wait_for_selector(".keyline", timeout=20000)
        key = pg.inner_text(".keyline")
        if not key or len(key) < 20:
            problems.append(f"key looks wrong: {key!r}")
        pg.click("#api-try button:not(.primary)")
        pg.wait_for_selector(".runs tbody tr", timeout=40000)
        pg.wait_for_timeout(6000)
        rows = pg.eval_on_selector_all(".runs tbody tr",
                                       "els => els.map(r => r.querySelectorAll('td')[1].innerText)")
        bad = [s for s in rows if s != "200"]
        print(f"     key {key[:22]}...  {len(rows)} endpoints, {len(bad)} not 200")
        if bad:
            problems.append(f"endpoints not 200: {bad}")

        print("  3. playing the day, step by step")
        pg.goto(base + "/app.html", wait_until="networkidle")
        pg.wait_for_timeout(800)
        played = 0
        while played < 12:
            btn = pg.query_selector("#steps .btn:not([disabled])")
            if not btn or btn.inner_text().startswith("Done") or "Play the rest" in btn.inner_text():
                break
            label = btn.inner_text()
            t0 = time.time()
            btn.click()
            for _ in range(180):
                pg.wait_for_timeout(700)
                if pg.evaluate("()=>[...document.querySelectorAll('#steps .btn')]"
                               ".some(x=>!x.disabled)"):
                    break
            took = time.time() - t0
            played += 1
            print(f"     {label:<26} {took:5.1f}s")
            if took > 90:
                notes.append(f"step {label} took {took:.0f}s, which is slow for a recording")

        print("  4. every tab fills")
        for tab in plan["tabs"]:
            pg.click("#" + tab)
            pg.wait_for_timeout(1200)
            sel = "#" + pg.get_attribute("#" + tab, "aria-controls")
            info = pg.evaluate("""(sel) => {
                const p = document.querySelector(sel);
                if (!p) return null;
                return {text: (p.innerText || '').trim().length,
                        kids: p.children.length,
                        h: Math.round(p.getBoundingClientRect().height)};
            }""", sel)
            if info is None:
                problems.append(f"{tab}: panel {sel} does not exist")
                continue
            state = "ok" if info["text"] > 40 else "LOOKS EMPTY"
            print(f"     {tab:<16} {info['kids']:>3} children, {info['text']:>5} chars, "
                  f"{info['h']:>4}px  {state}")
            if info["text"] <= 40:
                problems.append(f"{tab}: panel has only {info['text']} characters after a full run")

        print("  5. the dark theme, on the busiest screen")
        pg.evaluate("window.ThemeControl.apply('dark')")
        pg.wait_for_timeout(700)
        contrastish = pg.evaluate("""() => {
            const b = getComputedStyle(document.body);
            return {bg: b.backgroundColor, fg: b.color};
        }""")
        print(f"     body {contrastish['fg']} on {contrastish['bg']}")
        pg.evaluate("window.ThemeControl.apply('light')")

        ctx.close()
        browser.close()

    print()
    if notes:
        print("notes:")
        for n in notes:
            print("  " + n)
    if problems:
        print(f"{len(problems)} problems:")
        seen = set()
        for x in problems:
            if x not in seen:
                seen.add(x)
                print("  " + x)
        return 1
    print("clean: every page loaded, every step ran, every tab filled, nothing threw")
    return 0


if __name__ == "__main__":
    sys.exit(main())
