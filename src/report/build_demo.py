"""Build demo/index.html — a self-contained static dashboard from AGGREGATE report files only (no row-level data, no external scripts).

Usage: .venv/bin/python -I src/report/build_demo.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
R1, R2, R4 = ROOT / "reports" / "phase1", ROOT / "reports" / "phase2", ROOT / "reports" / "phase4"
OUT = ROOT / "demo"
OUT.mkdir(exist_ok=True)
J = lambda p: json.loads(Path(p).read_text())  # noqa: E731


def md_table(path, heading):
    lines = Path(path).read_text().splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith("#") and heading in l)
    out = []
    for l in lines[i + 1:]:
        if l.startswith("|"):
            out.append(l)
        elif out:
            break
    cells = [[c.strip() for c in l.strip("|").split("|")] for l in out if not set(l) <= set("|:- ")]
    return pd.DataFrame(cells[1:], columns=cells[0])


m = J(R1 / "metrics.json")
mon = pd.DataFrame(J(R1 / "monitoring.json"))
asof = J(R4 / "asof_model.json")
am = pd.DataFrame(asof["monitoring"])
mb = J(R2 / "macro_B.json")
eb = J(R2 / "ecl_benchmark.json")
e60 = J(R4 / "mob6_60m_test.json")
ov = J(R2 / "overlay.json")["total"]
vt = md_table(R1 / "vintage.md", "Cumulative default at MOB 12")


def qe(q):  # issue-quarter label -> first day of its last month
    return pd.Period(q, freq="Q").end_time.to_period("M").to_timestamp()


def knowable(q, months):
    return (qe(q) + pd.DateOffset(months=months)).strftime("%Y-%m")


ref = mon[mon.AE12_M2.notna()]
data = {
    "tiles": [
        {"label": "Champion OOT Gini (2015)", "value": f"{100*m['oot_2015']['M2_lgbm']['gini']:.1f}",
         "note": f"scorecard {100*m['oot_2015']['M1_scorecard']['gini']:.1f} · LC grade {100*m['oot_2015']['LC_subgrade']['gini']:.1f}"},
        {"label": "As-of model OOT Gini", "value": f"{100*asof['oot_final']['asof_PD12']['gini']:.1f}",
         "note": "only data known on 31 Dec 2014"},
        {"label": "Peak actual / expected", "value": f"{ref.AE12_M2.max():.2f}", "note": "defaults by month 12, champion"},
        {"label": "Realised / predicted loss", "value": f"{eb['(a) reference A, undiscounted LGD']['realised / predicted']:.2f}×",
         "note": f"{eb['(c) refit at 2014-12-31, discounted LGD (k=12)']['realised / predicted']:.2f}× with a refit at the reporting date"},
    ],
    "timeline": {
        "psi": [{"x": knowable(q, 0), "y": v, "q": q} for q, v in zip(mon.issue_q, mon.PSI_M2)],
        "ae_ref": [{"x": knowable(q, 18), "y": v, "q": q} for q, v in zip(ref.issue_q, ref.AE12_M2)],
        "ae_asof": [{"x": k, "y": v, "q": q} for q, v, k in zip(am.issue_q, am["A/E12"], am["knowable"]) if pd.notna(v)],
    },
    "bands": {"quarters": vt.issue_q.tolist(),
              "series": {f"B{b}": [None if v in ("", "nan") else float(v) for v in vt[f"B{b}@12"]] for b in range(1, 6)}},
    "models": [
        {"model": "Monotone LightGBM (champion)", **{k: m["oot_2015"]["M2_lgbm"][k] for k in ("gini", "gini_lo", "gini_hi", "ks")}},
        {"model": "WoE scorecard", **{k: m["oot_2015"]["M1_scorecard"][k] for k in ("gini", "gini_lo", "gini_hi", "ks")}},
        {"model": "LendingClub sub-grade (benchmark)", **{k: m["oot_2015"]["LC_subgrade"][k] for k in ("gini", "gini_lo", "gini_hi", "ks")}},
        {"model": "As-of model (data to Jun 2014)", **{k: asof["oot_final"]["asof_PD12"][k] for k in ("gini", "gini_lo", "gini_hi", "ks")}},
    ],
    "ecl": [{"name": k.split(") ", 1)[1], "pred": v.get("backtest: pred EL (undisc.) $m"), "ratio": v.get("realised / predicted"),
             "ecl12": v["day-1 12m ECL $m"], "ecllife": v["lifetime ECL $m"]}
            for k, v in eb.items() if isinstance(v, dict) and "scenario" in v],
    "realised": eb["realised_loss_m"],
    "overlay": {"ovl12": ov["EL_ovl12 $m"], "gap12": ov["gap closed MOB12"]},
    "macro": {"a": mb["rule_a"], "b": mb["rule_b"], "c": mb["rule_c"], "decision": mb["decision"]},
    "mob6": {"res": e60["results"]["M2"], "quarters": e60["by_quarter"]["issue_q"], "ae6": e60["by_quarter"]["A/E6 M2"],
             "truth": e60["by_quarter"]["truth"]},
}
html = (ROOT / "src" / "report" / "demo_template.html").read_text().replace("/*__DATA__*/null", json.dumps(data, default=float))
(OUT / "index.html").write_text(html)
print("wrote", OUT / "index.html", f"{len(html)/1e3:.0f} kB")
