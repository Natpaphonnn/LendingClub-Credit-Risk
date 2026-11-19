"""MOB-6 A/E — out-of-discovery test on issue quarters 2016Q1..2017Q4 only (prereg §MOB-6; discovered on 2015 vintages).

Output: reports/phase2/mob6_test.md
Usage: nice -n 19 .venv/bin/python -I src/phase2/mob6_test.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "phase1"))
from config import ART, ASOF, CHARGEOFF_LAG_M, TRAIN, load_base, split_mask  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "lib"))
from riskutils import default_by_mob  # noqa: E402

REP2 = ROOT / "reports" / "phase2"
df = load_base(["issue_dt", "issue_q", "bad", "default_mob"])
df = df.join(pd.read_parquet(ART / "scores_m1.parquet", columns=["pd_m1"])).join(pd.read_parquet(ART / "scores_m2.parquet"))
df["q_end"] = df.issue_dt.dt.to_period("Q").dt.end_time.dt.to_period("M").dt.to_timestamp()
df["d6"] = default_by_mob(df.default_mob, 6)
df["d12"] = default_by_mob(df.default_mob, 12)
trm = split_mask(df, TRAIN)
r6 = df.loc[trm, "d6"].mean() / df.loc[trm, "bad"].mean()
d12_train = df.loc[trm, "d12"].mean()
asof = pd.Timestamp(ASOF)
flag = lambda v: "RED" if v > 1.25 else "AMBER" if v > 1.10 else "green"  # noqa: E731

rows = []
for q in [f"{y}Q{k}" for y in (2014, 2015, 2016, 2017) for k in (1, 2, 3, 4)]:
    d = df[df.issue_q == q]
    qe = d.q_end.iloc[0]
    k6, k12 = qe + pd.DateOffset(months=6 + CHARGEOFF_LAG_M), qe + pd.DateOffset(months=12 + CHARGEOFF_LAG_M)
    r = {"issue_q": q, "n": len(d), "MOB6 default %": round(100 * d.d6.mean(), 3)}
    for m, c in (("M1", "pd_m1"), ("M2", "pd_m2")):
        ae = d.d6.sum() / (d[c].sum() * r6)
        r[f"A/E6 {m}"], r[f"flag {m}"] = round(ae, 3), flag(ae)
    r["MOB6 known"] = k6.strftime("%Y-%m")
    if k12 <= asof:
        x = d.d12.mean() / d12_train
        r["MOB12 ×train"], r["truth (≥1.2×)"] = round(x, 2), "YES" if x >= 1.2 else "no"
        r["MOB12 known"] = k12.strftime("%Y-%m")
        r["lead (months)"] = (k12.year - k6.year) * 12 + (k12.month - k6.month)
    else:
        r["truth (≥1.2×)"] = "not observable"
    rows.append(r)
T = pd.DataFrame(rows)
disc = T[T.issue_q < "2016Q1"]                       # discovery period (signal found here in Phase 1)
T = T[T.issue_q >= "2016Q1"].reset_index(drop=True)
conf = []
for m in ("M1", "M2"):
    pos, neg = disc[disc["truth (≥1.2×)"] == "YES"], disc[disc["truth (≥1.2×)"] == "no"]
    conf.append({"model": m, "period": "2014Q1–2015Q4 (discovery)",
                 "sensitivity": f"{pos[f'flag {m}'].isin(['AMBER','RED']).sum()}/{len(pos)}",
                 "specificity": f"{(~neg[f'flag {m}'].isin(['AMBER','RED'])).sum()}/{len(neg)}",
                 "missed quarters": ", ".join(pos.loc[~pos[f'flag {m}'].isin(['AMBER','RED']), 'issue_q']) or "none"})
ev = T[T["truth (≥1.2×)"].isin(["YES", "no"])]
summ = []
for m in ("M1", "M2"):
    pos = ev[ev["truth (≥1.2×)"] == "YES"]
    hit = pos[f"flag {m}"].isin(["AMBER", "RED"])
    neg = ev[ev["truth (≥1.2×)"] == "no"]
    summ.append({"model": m, "quarters with truth": len(ev), "truth YES": len(pos),
                 "sensitivity (amber+)": f"{hit.sum()}/{len(pos)} = {100*hit.mean():.0f}%" if len(pos) else "n/a",
                 "≥80% hit rate? (descriptive)": ("YES" if hit.mean() >= 0.8 else "NO") if len(pos) else "n/a",
                 "truth no": len(neg), "specificity": "not testable (no non-deteriorated quarter)" if len(neg) == 0
                 else f"{(~neg[f'flag {m}'].isin(['AMBER','RED'])).sum()}/{len(neg)}",
                 "median lead (months)": float(np.median(pos.loc[hit, "lead (months)"])) if hit.any() else None})
md = ("# MOB-6 A/E — 2016Q1–2017Q4 (EXPLORATORY / DESCRIPTIVE — not a confirmatory test)\n\n"
      "**Status (corrected after independent review, CR-1):** the thresholds were registered in notes/03_prereg_phase2.md (commit 1203ada), "
      "but the 2016–17 MOB-6 A/E values had already been computed and committed in reports/phase1/exploratory_early_signal.md "
      "(commit 5b35a6e) before that registration. This table is therefore descriptive, not an out-of-discovery test. "
      "Lead time is 6 months **by construction** (MOB-6 is knowable 6 months before MOB-12); the truth (MOB-12 rate) shares the "
      "same default events; every 2016–17 quarter is deteriorated, so any always-on alarm would also score 7/7. "
      "The A/E level also depends on how 'expected' is built: under the lifetime hazard model's own MOB shape, 2015 A/E6 is 0.91–1.09 "
      "(reports/phase2/overlay.md).\n\n"
      "## Discovery-period confusion matrix (2014Q1–2015Q4; truth = MOB-12 ≥ 1.2× train)\n\n"
      + pd.DataFrame(conf).to_markdown(index=False) + "\n\n"
      f"r6 (train MOB-6 defaults / final bads) = {r6:.4f}; train MOB-12 default rate = {100*d12_train:.2f}%. "
      "Thresholds: A/E6 > 1.10 AMBER, > 1.25 RED.\n\n## Summary 2016Q1–2017Q3 (descriptive)\n\n" + pd.DataFrame(summ).to_markdown(index=False)
      + "\n\n## By quarter (2016–17)\n\n" + T.to_markdown(index=False) + "\n\n## Discovery period by quarter\n\n"
      + disc.to_markdown(index=False) + "\n")
(REP2 / "mob6_test.md").write_text(md)
print(md)
