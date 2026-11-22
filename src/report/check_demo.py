"""Browser check of demo/index.html (Playwright, headless Chromium): no console errors, no horizontal scroll at 390 px and 1300 px,
light and dark themes, pre-registered defaults shown; full-page screenshots to reports/demo_screens/.
Playwright is not in requirements.lock.txt (dev-only):  pip install playwright && python -m playwright install chromium
Usage: python src/report/check_demo.py
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
URL = (ROOT / "demo" / "index.html").as_uri()
OUT = ROOT / "reports" / "demo_screens"
OUT.mkdir(parents=True, exist_ok=True)
problems = []
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (390, 1300):
        for scheme in ("light", "dark"):
            pg = b.new_page(viewport={"width": w, "height": 900}, color_scheme=scheme)
            errs = []
            pg.on("console", lambda m, errs=errs: errs.append(m.text) if m.type in ("error", "warning") else None)
            pg.on("pageerror", lambda e, errs=errs: errs.append(str(e)))
            pg.goto(URL)
            pg.wait_for_timeout(300)
            sw, iw = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
            tab = pg.inner_text("#alarmtab")
            tag = pg.inner_text("#prereg")
            kv = pg.inner_text("#polkv")
            # interact: move sliders, switch funding cost, then reset
            pg.fill("#amb", "1.20"); pg.dispatch_event("#amb", "input")
            pg.select_option("#rate", "0.08")
            pg.click("#resetT"); pg.click("#resetP"); pg.select_option("#rate", "0.05")
            pg.screenshot(path=str(OUT / f"demo_{w}px_{scheme}.png"), full_page=True)
            if errs:
                problems.append(f"{w}px {scheme}: console {errs}")
            if sw > iw:
                problems.append(f"{w}px {scheme}: horizontal scroll ({sw} > {iw})")
            for must in ("Dec 2016", "544,642", "Jun 2017"):
                if must not in tab:
                    problems.append(f"{w}px {scheme}: alarm table missing {must!r}")
            if tag != "pre-registered thresholds":
                problems.append(f"{w}px {scheme}: default thresholds not labelled pre-registered")
            if "$47.5m" not in kv or "$45.8m" not in kv:
                problems.append(f"{w}px {scheme}: policy panel defaults {kv!r}")
            pg.close()
    b.close()
print("\n".join(problems) if problems else "demo check: OK (390 px and 1300 px, light and dark)")
sys.exit(1 if problems else 0)
