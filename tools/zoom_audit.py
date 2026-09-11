"""WCAG 1.4.4 asks for 200 percent zoom without loss of content or function. The audit checks three
widths at 100 percent, which is not the same thing: zoom changes the CSS pixel ratio, so a layout
that survives a narrow window can still break when the text doubles."""
import sys

from playwright.sync_api import sync_playwright

BASE = sys.argv[1]
PAGES = sys.argv[2].split(",")
bad = []
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for path in PAGES:
        for zoom in (2.0, 4.0):
            # 1280 at 200 percent is a 640 CSS pixel viewport with 2x text.
            ctx = b.new_context(viewport={"width": int(1280 / zoom), "height": int(900 / zoom)},
                                device_scale_factor=zoom)
            pg = ctx.new_page()
            pg.goto(BASE + path, wait_until="networkidle")
            pg.wait_for_timeout(500)
            r = pg.evaluate("""() => ({
                sw: document.documentElement.scrollWidth,
                cw: document.documentElement.clientWidth,
                clipped: [...document.querySelectorAll('h1,h2,h3,p,.btn,td,th')]
                  .filter(e => e.scrollWidth > e.clientWidth + 2 &&
                               getComputedStyle(e).overflowX !== 'auto' &&
                               getComputedStyle(e).overflowX !== 'scroll')
                  .slice(0, 4).map(e => e.tagName + ': ' + e.textContent.trim().slice(0, 40))
            })""")
            pct = int(zoom * 100)
            if r["sw"] > r["cw"] + 1:
                bad.append(f"{path} at {pct}%: scrolls sideways, {r['sw']} in {r['cw']}")
            for c in r["clipped"]:
                bad.append(f"{path} at {pct}%: clipped {c}")
            ctx.close()
    b.close()

print(f"checked {len(PAGES)} pages at 200 and 400 percent")
if bad:
    print(f"{len(bad)} problems:")
    for x in bad:
        print("  " + x)
    raise SystemExit(1)
print("no sideways scroll and nothing clipped at either zoom")
