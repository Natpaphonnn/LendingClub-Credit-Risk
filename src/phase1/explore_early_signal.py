"""EXPLORATORY (not pre-registered): could an earlier label-based signal have flagged the drift sooner?
MOB-6 default A/E, using the same construction and thresholds as the pre-registered MOB-12 signal.
Knowable at quarter end + 6 + 6 months.

Output: reports/phase1/exploratory_early_signal.md
Usage: nice -n 19 .venv/bin/python -I src/phase1/explore_early_signal.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import ART, ASOF, CHARGEOFF_LAG_M, REP, TRAIN, load_base, split_mask  # noqa: E402

df = load_base(["issue_dt", "issue_q", "bad", "default_mob"])
df = df.join(pd.read_parquet(ART / "scores_m1.parquet", columns=["pd_m1"])).join(pd.read_parquet(ART / "scores_m2.parquet"))
df["q_end"] = df.issue_dt.dt.to_period("Q").dt.end_time.dt.to_period("M").dt.to_timestamp()
trm = split_mask(df, TRAIN)
rows = []
for mob in (6, 9):
    df[f"d{mob}"] = (df.default_mob <= mob).astype(float)
    r = df.loc[trm, f"d{mob}"].mean() / df.loc[trm, "bad"].mean()
    for q, d in df[df.issue_dt >= pd.Timestamp("2014-01-01")].groupby("issue_q"):
        known = d.q_end.iloc[0] + pd.DateOffset(months=mob + CHARGEOFF_LAG_M)
        if known > pd.Timestamp(ASOF):
            continue
        ae1 = d[f"d{mob}"].sum() / (d.pd_m1.sum() * r)
        ae2 = d[f"d{mob}"].sum() / (d.pd_m2.sum() * r)
        fl = lambda v: "RED" if v > 1.25 else "AMBER" if v > 1.10 else "green"  # noqa: E731
        rows.append({"MOB": mob, "issue_q": q, "default %": round(100 * d[f"d{mob}"].mean(), 2),
                     "A/E M1": round(ae1, 2), "flag M1": fl(ae1), "A/E M2": round(ae2, 2), "flag M2": fl(ae2),
                     "known at": known.strftime("%Y-%m")})
T = pd.DataFrame(rows)
first = []
for mob in (6, 9):
    for m in ("M1", "M2"):
        for lv in (("AMBER", "RED"), ("RED",)):
            s = T[(T.MOB == mob) & T[f"flag {m}"].isin(lv)]
            first.append({"signal": f"A/E MOB{mob} {m}", "level": "/".join(lv),
                          "first issue quarter": s.issue_q.iloc[0] if len(s) else "never",
                          "knowable at": s["known at"].iloc[0] if len(s) else ""})
md = ("# EXPLORATORY — earlier label-based signals (not pre-registered)\n\n"
      "Same A/E construction and thresholds as the pre-registered MOB-12 signal, at MOB 6 and 9. Treat as hypothesis-"
      "generating only: thresholds were not tuned, but the choice to look was made after seeing the MOB-12 result.\n\n"
      "## First flag\n\n" + pd.DataFrame(first).to_markdown(index=False) + "\n\n## By quarter\n\n"
      + T.to_markdown(index=False) + "\n")
(REP / "exploratory_early_signal.md").write_text(md)
print(md)
