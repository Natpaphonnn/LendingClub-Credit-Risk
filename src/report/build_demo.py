"""Build demo/index.html — a self-contained static dashboard from AGGREGATE report files only (no row-level data, no external scripts).

Usage: .venv/bin/python -I src/report/build_demo.py
"""
import json
import re
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
vt = md_table(R1 / "vintage.md", "Cumulative default at MOB 12")


def qe(q):  # issue-quarter label -> first day of its last month
    return pd.Period(q, freq="Q").end_time.to_period("M").to_timestamp()


def knowable(q, months):
    return (qe(q) + pd.DateOffset(months=months)).strftime("%Y-%m")


ref = mon[mon.AE12_M2.notna()]
pol = J(R2 / "policy_C.json")
dif = pol["0.05"]["diffs"]
k = next(i for i, (n, b) in enumerate(zip(dif["difference ($m, OOT 2015)"], dif["bootstrap"])) if n == "C−M2 NPV" and b == "loan")
life = re.search(r"n = ([\d,]+);.*?censoring ([\d.]+)%, competing-risks ([\d.]+)%, actual cumulative default by month 36 ([\d.]+)%",
                 (R2 / "survival_A.md").read_text())
eq = md_table(R2 / "ecl.md", "Backtest by issue quarter")
aud = md_table(ROOT / "reports" / "audit" / "audit_tables.md", "Accepted file — basics").set_index("item")["value"]
loans_total = int(aud["rows with valid issue_d (loans)"].replace(",", ""))
EBK = {"a": "(a) reference A, undiscounted LGD", "c": "(c) refit at 2014-12-31 as pre-registered (MOB 1–21) + reference tail, discounted LGD (k=12)",
       "c2": "(c'') (c) with the MOB 22–36 tail from the 2009-start refit (knowable at 2014-12)"}
G = lambda d: {k_: d[k_] for k_ in ("gini", "gini_lo", "gini_hi", "ks")}  # noqa: E731
vq = [i for i, v in enumerate(vt["B1@12"]) if v not in ("", "nan")]
data = {
    "loans_total": loans_total,
    "models": [{"model": "Monotone LightGBM (champion)", "key": "champion", **G(m["oot_2015"]["M2_lgbm"])},
               {"model": "LendingClub sub-grade", "key": "lc", **G(m["oot_2015"]["LC_subgrade"])},
               {"model": "WoE scorecard", "key": "scorecard", **G(m["oot_2015"]["M1_scorecard"])},
               {"model": "As-of model (data known at end-2014)", "key": "asof", **G(asof["oot_final"]["asof_PD12"])}],
    "timeline": {"psi": [{"x": k_, "y": float(v), "q": q} for q, v, k_ in zip(mon.issue_q, mon.PSI_M2, mon.known_PSI)],
                 "ae_ref": [{"x": k_, "y": float(v), "q": q} for q, v, k_ in zip(ref.issue_q, ref.AE12_M2, ref.known_MOB12)],
                 "ae_asof": [{"x": k_, "y": float(v), "q": q} for q, v, k_ in zip(am.issue_q, am["A/E12"], am["knowable"]) if pd.notna(v)]},
    "psi_max": float(mon.PSI_M2.max()),
    "bands": {"quarters": [vt.issue_q[i] for i in vq], "series": [[float(vt[f"B{b}@12"][i]) for i in vq] for b in range(1, 6)]},
    "ecl_q": [{"q": q, "pred": float(p_), "real": float(r_)} for q, p_, r_ in zip(eq.issue_q, eq["pred EL (undisc) $m"], eq["realised loss $m"])],
    "ecl_ratio": {k_: eb[v]["realised / predicted"] for k_, v in EBK.items()},
    "life": {"n": int(life.group(1).replace(",", "")), "cens": float(life.group(2)), "cr": float(life.group(3)), "act": float(life.group(4))},
    "macro": {"theta": mb["rule_a"]["theta"], "mult": mb["rule_c"]["multiplier"]},
    "mob6": e60["results"]["M2"],
    "policy_diff": {"point": dif["point"][k], "ci": dif["95% CI"][k]},
    "manifest_n": sum(1 for l in (ROOT / "reports" / "quality" / "reports_manifest.sha256").read_text().splitlines() if l.strip()),
    # alarm-threshold panel: quarterly A/E12 with knowable dates, loans per issue quarter, first worse vintage (truth ≥ 1.2× train)
    "alarm": {"first_worse": str(mon.loc[mon.deterioration == "YES", "issue_q"].iloc[0]),
              "n": dict(zip(mon.issue_q, mon.n.astype(int))),
              "reference": [{"q": q_, "ae": float(v), "known": k_} for q_, v, k_ in zip(mon.issue_q, mon.AE12_M2, mon.known_MOB12) if pd.notna(v)],
              "asof": [{"q": q_, "ae": float(v), "known": k_} for q_, v, k_ in zip(am.issue_q, am["A/E12"], am["knowable"]) if pd.notna(v)]},
    # policy panel (exploratory): single PD cutoff swept on 2015 loans, by funding cost; pre-registered cutoff and MILP marked
    "policy": {k_: {"curve": v["curve"], "marks": v["marks"]} for k_, v in pol.items()},
}
html = (ROOT / "src" / "report" / "demo_template.html").read_text().replace("/*__DATA__*/null", json.dumps(data, default=float))
(OUT / "index.html").write_text(html)
print("wrote", OUT / "index.html", f"{len(html)/1e3:.0f} kB")
