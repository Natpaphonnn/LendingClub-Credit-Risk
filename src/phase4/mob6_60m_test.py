"""E1 — Confirmatory MOB-6 A/E test on 60-month loans (notes/08_prereg_extensions.md §E1, pushed before this ran).

Output: reports/phase4/mob6_60m_test.md, reports/phase4/mob6_60m_test.json ; row-level 60m table: data/interim/p4_60m.parquet
Usage: nice -n 19 .venv/bin/python -I src/phase4/mob6_60m_test.py
"""
import json
import pickle
import sys
from pathlib import Path

import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import beta

ROOT = Path(__file__).resolve().parents[2]
for p in ("src/phase1", "src/lib"):
    sys.path.insert(0, str(ROOT / p))
from config import ACC, ART, ASOF, CATEGORICAL, CHARGEOFF_LAG_M, FEATURES, INTERIM, NUMERIC  # noqa: E402
from riskutils import default_by_mob  # noqa: E402

REP4 = ROOT / "reports" / "phase4"
REP4.mkdir(parents=True, exist_ok=True)
num = ",\n  ".join(f"TRY_CAST({c} AS DOUBLE)::FLOAT AS {c}" for c in NUMERIC)
sql = f"""
WITH a AS (SELECT *, strptime(issue_d, '%b-%Y')::DATE AS issue_dt, TRY_STRPTIME(last_pymnt_d, '%b-%Y')::DATE AS lp_dt
           FROM read_parquet('{ACC}', file_row_number=true) WHERE TRY_STRPTIME(issue_d, '%b-%Y') IS NOT NULL)
SELECT TRY_CAST(id AS BIGINT) AS id, issue_dt, year(issue_dt)::VARCHAR || 'Q' || quarter(issue_dt)::VARCHAR AS issue_q,
  CASE WHEN loan_status IN ('Charged Off','Default') THEN coalesce(date_diff('month', issue_dt, lp_dt) + 1, 1) END AS default_mob,
  {num},
  (TRY_CAST(fico_range_low AS DOUBLE) + 2)::FLOAT AS fico,
  date_diff('month', TRY_STRPTIME(earliest_cr_line, '%b-%Y')::DATE, issue_dt)::FLOAT AS credit_hist_months,
  (TRY_CAST(loan_amnt AS DOUBLE) / NULLIF(TRY_CAST(annual_inc AS DOUBLE), 0))::FLOAT AS loan_to_income,
  CASE WHEN emp_length = '< 1 year' THEN 0 WHEN emp_length = '10+ years' THEN 10
       ELSE TRY_CAST(regexp_extract(emp_length, '^([0-9]+)', 1) AS INT) END::FLOAT AS emp_length_yrs,
  home_ownership, verification_status, purpose
FROM a WHERE trim(term) = '60 months' AND application_type = 'Individual' AND loan_status NOT LIKE 'Does not meet%'
  AND issue_dt BETWEEN DATE '2012-09-01' AND DATE '2017-09-01'
ORDER BY file_row_number
"""
con = duckdb.connect()
con.execute("SET memory_limit='4GB'; SET threads=4;")
df = con.execute(sql).df()
df["issue_dt"] = pd.to_datetime(df.issue_dt)

# frozen scores: M2 (champion) primary, M1 (scorecard) secondary
booster = lgb.Booster(model_file=str(ART / "lgbm.txt"))
cats = json.loads((ART / "lgbm_cats.json").read_text())
X = df[FEATURES].copy()
for c in CATEGORICAL:
    X[c] = pd.Categorical(X[c], categories=cats[c])
df["pd_m2"] = booster.predict(X)
sc = pickle.load(open(ART / "scorecard.pkl", "rb"))
s1 = np.zeros(len(df))
for c in sc["cols"]:
    s1 += sc["bins"][c].assign(df[c]).map(sc["points"][c]).fillna(0).to_numpy(float)
df["pd_m1"] = 1 / (1 + np.exp((s1 - sc["offset"]) / sc["factor"]))
df["d6"], df["d12"] = default_by_mob(df.default_mob, 6), default_by_mob(df.default_mob, 12)
df["q_end"] = df.issue_dt.dt.to_period("Q").dt.end_time.dt.to_period("M").dt.to_timestamp()
df[["id", "issue_dt", "issue_q", "default_mob", "pd_m2", "pd_m1"]].to_parquet(INTERIM / "p4_60m.parquet")

ref = df[(df.issue_dt >= "2012-09-01") & (df.issue_dt <= "2013-12-01")]
ref12 = ref.d12.mean()
flag = lambda v: "RED" if v > 1.25 else "AMBER" if v > 1.10 else "green"  # noqa: E731
quarters = [f"{y}Q{k}" for y in range(2014, 2018) for k in (1, 2, 3, 4)][:15]          # 2014Q1 .. 2017Q3
rows = []
r6 = {m: ref.d6.mean() / ref[f"pd_{m}"].mean() for m in ("m2", "m1")}
for q in quarters:
    d = df[df.issue_q == q]
    qe = d.q_end.iloc[0]
    r = {"issue_q": q, "n": len(d), "MOB6 default %": 100 * d.d6.mean()}
    for m in ("m2", "m1"):
        ae = d.d6.sum() / (d[f"pd_{m}"].sum() * r6[m])
        r[f"A/E6 {m.upper()}"], r[f"flag {m.upper()}"] = ae, flag(ae)
    r["MOB12 × ref"] = d.d12.mean() / ref12
    r["truth"] = "YES" if r["MOB12 × ref"] >= 1.2 else "no"
    r["MOB6 knowable"] = (qe + pd.DateOffset(months=6 + CHARGEOFF_LAG_M)).strftime("%Y-%m")
    r["truth knowable"] = (qe + pd.DateOffset(months=12 + CHARGEOFF_LAG_M)).strftime("%Y-%m")
    assert qe + pd.DateOffset(months=12 + CHARGEOFF_LAG_M) <= pd.Timestamp(ASOF)
    rows.append(r)
T = pd.DataFrame(rows)


def cp(k, n):
    if n == 0:
        return (np.nan, np.nan)
    lo = beta.ppf(0.025, k, n - k + 1) if k > 0 else 0.0
    hi = beta.ppf(0.975, k + 1, n - k) if k < n else 1.0
    return lo, hi


res = {}
for m in ("M2", "M1"):
    pos, neg = T[T.truth == "YES"], T[T.truth == "no"]
    tp = int(pos[f"flag {m}"].isin(["AMBER", "RED"]).sum())
    tn = int((neg[f"flag {m}"] == "green").sum())
    sens = tp / len(pos) if len(pos) else np.nan
    spec = tn / len(neg) if len(neg) else np.nan
    if len(pos) < 3 or len(neg) < 3:
        verdict = "INCONCLUSIVE"
    else:
        verdict = "PASS" if (sens >= 0.80 and spec >= 0.80) else "FAIL"
    first_flag = T[T[f"flag {m}"].isin(["AMBER", "RED"])]
    first_truth = T[T.truth == "YES"]
    res[m] = {"n_truth_yes": len(pos), "n_truth_no": len(neg), "tp": tp, "tn": tn, "sensitivity": sens,
              "sensitivity_ci": cp(tp, len(pos)), "specificity": spec, "specificity_ci": cp(tn, len(neg)), "verdict": verdict,
              "first_flag_q": None if first_flag.empty else first_flag.issue_q.iloc[0],
              "first_flag_knowable": None if first_flag.empty else first_flag["MOB6 knowable"].iloc[0],
              "first_truth_q": None if first_truth.empty else first_truth.issue_q.iloc[0],
              "first_truth_knowable": None if first_truth.empty else first_truth["truth knowable"].iloc[0]}
(REP4 / "mob6_60m_test.json").write_text(json.dumps({"r6": r6, "ref12": ref12, "n_ref": len(ref), "results": res,
                                                      "by_quarter": T.to_dict(orient="list")}, indent=1, default=float))


def fr(x):
    return f"{100*x[0]:.0f}–{100*x[1]:.0f}%"


summ = pd.DataFrame([{"score": m + (" (primary)" if m == "M2" else " (secondary)"), "truth YES / no quarters": f"{v['n_truth_yes']} / {v['n_truth_no']}",
                      "sensitivity": f"{v['tp']}/{v['n_truth_yes']}" + (f" = {100*v['sensitivity']:.0f}% (95% CI {fr(v['sensitivity_ci'])})" if v['n_truth_yes'] else ""),
                      "specificity": f"{v['tn']}/{v['n_truth_no']}" + (f" = {100*v['specificity']:.0f}% (95% CI {fr(v['specificity_ci'])})" if v['n_truth_no'] else ""),
                      "verdict": f"**{v['verdict']}**", "first MOB-6 flag (knowable)": f"{v['first_flag_q']} ({v['first_flag_knowable']})",
                      "first truth YES (knowable)": f"{v['first_truth_q']} ({v['first_truth_knowable']})"} for m, v in res.items()])
Tf = T.copy()
for c in Tf.columns:
    if Tf[c].dtype.kind == "f":
        Tf[c] = Tf[c].round(3)
md = (f"# E1 — Confirmatory MOB-6 A/E test on 60-month loans (pre-registered, commit 4562602, pushed before this ran)\n\n"
      f"Reference window 60m issued 2012-09..2013-12: n = {len(ref):,}, MOB-12 default rate {100*ref12:.2f}%, r6 (M2) = {r6['m2']:.4f}, r6 (M1) = {r6['m1']:.4f}. "
      "Thresholds amber > 1.10, red > 1.25; truth = MOB-12 rate ≥ 1.2 × reference. Criterion: sensitivity ≥ 0.80 and specificity ≥ 0.80 with ≥ 3 quarters "
      "per class (else INCONCLUSIVE). Lead time is 6 months by construction.\n\n## Result\n\n" + summ.to_markdown(index=False)
      + "\n\n## By issue quarter (2014Q1–2017Q3)\n\n" + Tf.to_markdown(index=False) + "\n")
(REP4 / "mob6_60m_test.md").write_text(md)
print(md)
