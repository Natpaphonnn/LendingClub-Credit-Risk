"""Browser check of demo/index.html (Playwright, headless Chromium) at 390 px and 1300 px: no console errors, no horizontal scroll,
pre-registered defaults shown, legend colours match the drawn marks, reduced-motion mode renders; full-page screenshots to
reports/demo_screens/. Also writes every rendered text (all stepper steps + SVG labels) to reports/demo_screens/demo_text.txt, which
src/quality/check_note_numbers.py checks for number provenance.
The page has one light palette (navy + paper + risk red); no dark mode by design.
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
NAVY, RED, INK3 = "#0b2545", "#c8372d", "#6b7a90"
problems, texts = [], []
with sync_playwright() as p:
    b = p.chromium.launch()
    for w, motion in ((390, "no-preference"), (1300, "no-preference"), (390, "reduce")):
        pg = b.new_page(viewport={"width": w, "height": 900}, reduced_motion=motion)
        errs = []
        pg.on("console", lambda m, errs=errs: errs.append(m.text) if m.type in ("error", "warning") else None)
        pg.on("pageerror", lambda e, errs=errs: errs.append(str(e)))
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_timeout(400)
        tag = f"{w}px {motion}"
        sw, iw = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        tab, pre, kv = pg.inner_text("#alarmtab"), pg.inner_text("#prereg"), pg.inner_text("#polkv")
        for must in ("Dec 2016", "544,642", "Jun 2017", "687,800"):
            if must not in tab:
                problems.append(f"{tag}: alarm table missing {must!r}")
        if pre != "pre-registered thresholds":
            problems.append(f"{tag}: default thresholds not labelled pre-registered")
        vals = pg.evaluate("""() => { const P = D.policy["0.05"], i = +document.getElementById("cut").value, c = P.curve,
            pre = P.marks["pre-registered cutoff"];
            return [c.cutoff[i] === pre.cutoff, c["approval %"][i] === pre["approval %"], c["approved bad %"][i] === pre["approved bad %"],
                    c["realised NPV $m"][i] === pre["realised NPV $m"]]; }""")
        if not all(vals) or "$47.5m" not in kv or "$45.8m" not in kv or pg.inner_text("#cutv") != "0.1994":
            problems.append(f"{tag}: policy default is not the exact pre-registered cutoff {vals} {kv!r}")
        legend_ok = pg.evaluate(f"""() => {{ const sv = document.getElementById("pol");
            const stroke = [...sv.querySelectorAll("path")].map(e => e.getAttribute("stroke"));
            const dots = [...sv.querySelectorAll("circle")].map(e => e.getAttribute("fill"));
            const dash = [...sv.querySelectorAll("line")].filter(e => e.getAttribute("stroke-dasharray")).map(e => e.getAttribute("stroke"));
            return stroke.includes("{NAVY}") && dots.includes("{RED}") && dash.includes("{INK3}"); }}""")
        if not legend_ok:
            problems.append(f"{tag}: policy legend colours do not match the drawn marks")
        if pg.locator("#exPost").inner_text().strip() != ("Ex-post curve on 2015 outcomes; its best point is only knowable afterwards. "
                                                         "The pre-registered cutoff was set on 2014."):
            problems.append(f"{tag}: ex-post note missing")
        # interact, then reset
        pg.fill("#amb", "1.20"); pg.dispatch_event("#amb", "input"); pg.select_option("#rate", "0.08")
        pg.click("#resetT"); pg.click("#resetP"); pg.select_option("#rate", "0.05")
        # every stepper step: collect text; finish on the last step so the screenshot shows the whole timeline
        n = pg.locator("#chips .chip").count()
        for k in range(n):
            pg.locator("#chips .chip").nth(k).click()
            pg.wait_for_timeout(50 if motion == "reduce" else 1000)
            if w == 1300:
                texts.append(" | ".join(pg.inner_text(s) for s in ("#sd", "#sh", "#sp")))
        if motion == "reduce" and pg.evaluate("document.querySelector('#rev rect').getAttribute('width')") in (None, "0"):
            problems.append(f"{tag}: timeline not revealed with reduced motion")
        sw2 = pg.evaluate("document.documentElement.scrollWidth")
        if max(sw, sw2) > iw:
            problems.append(f"{tag}: horizontal scroll ({max(sw, sw2)} > {iw})")
        if motion == "no-preference":
            pg.screenshot(path=str(OUT / f"demo_{w}px.png"), full_page=True)
        if w == 1300:
            texts.append(pg.inner_text("body"))
            texts.append("\n".join(pg.evaluate("[...document.querySelectorAll('svg text')].map(t => t.textContent)")))
            texts.append(pg.evaluate("[...document.querySelectorAll('.kpi')].map(k => k.innerText).join('\\n')"))
        if errs:
            problems.append(f"{tag}: console {errs}")
        pg.close()
    b.close()
(OUT / "demo_text.txt").write_text("\n".join(texts) + "\n")
print("\n".join(problems) if problems else "demo check: OK (390 px and 1300 px; reduced motion at 390 px)")
sys.exit(1 if problems else 0)
