"""Phase 2 loan table: 36m, Individual, meets policy, issued 2009-01..2018-12; frozen M2 PD; competing-risk event coding
exactly as notes/03_prereg_phase2.md §A.

Output (row-level, git-ignored): data/interim/p2_loans.parquet
Usage: nice -n 19 .venv/bin/python -I src/phase2/build_loans.py
"""
import json
import sys
from pathlib import Path

import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "phase1"))
from config import ACC, ART, CATEGORICAL, FEATURES, INTERIM, NUMERIC  # noqa: E402
sys.path.insert(0, str(ROOT / "src" / "lib"))
from riskutils import code_events  # noqa: E402
from scoring import load_categories, score  # noqa: E402

OUT = INTERIM / "p2_loans.parquet"
num = ",\n  ".join(f"TRY_CAST({c} AS DOUBLE)::FLOAT AS {c}" for c in NUMERIC)
sql = f"""
WITH a AS (
  SELECT *, strptime(issue_d, '%b-%Y')::DATE AS issue_dt, TRY_STRPTIME(last_pymnt_d, '%b-%Y')::DATE AS lp_dt
  FROM read_parquet('{ACC}', file_row_number=true) WHERE TRY_STRPTIME(issue_d, '%b-%Y') IS NOT NULL
)
SELECT TRY_CAST(id AS BIGINT) AS id, issue_dt, year(issue_dt) AS yr, year(issue_dt)::VARCHAR || 'Q' || quarter(issue_dt)::VARCHAR AS issue_q,
  loan_status, addr_state, grade, sub_grade,
  CASE WHEN loan_status IN ('Charged Off','Default') THEN 1 WHEN loan_status = 'Fully Paid' THEN 0 END::FLOAT AS bad,
  date_diff('month', issue_dt, lp_dt) AS lp_mob,
  CASE WHEN loan_status IN ('Charged Off','Default') THEN coalesce(date_diff('month', issue_dt, lp_dt) + 1, 1) END AS default_mob,
  LEAST(36, date_diff('month', issue_dt, DATE '2018-09-01')) AS W,
  TRY_CAST(funded_amnt AS DOUBLE) AS funded_amnt, TRY_CAST(int_rate AS DOUBLE) AS int_rate,
  TRY_CAST(installment AS DOUBLE) AS installment, TRY_CAST(total_rec_prncp AS DOUBLE) AS total_rec_prncp,
  TRY_CAST(recoveries AS DOUBLE) AS recoveries, TRY_CAST(collection_recovery_fee AS DOUBLE) AS collection_recovery_fee,
  TRY_CAST(total_pymnt AS DOUBLE) AS total_pymnt,
  {num},
  (TRY_CAST(fico_range_low AS DOUBLE) + 2)::FLOAT AS fico,
  date_diff('month', TRY_STRPTIME(earliest_cr_line, '%b-%Y')::DATE, issue_dt)::FLOAT AS credit_hist_months,
  (TRY_CAST(loan_amnt AS DOUBLE) / NULLIF(TRY_CAST(annual_inc AS DOUBLE), 0))::FLOAT AS loan_to_income,
  CASE WHEN emp_length = '< 1 year' THEN 0 WHEN emp_length = '10+ years' THEN 10
       ELSE TRY_CAST(regexp_extract(emp_length, '^([0-9]+)', 1) AS INT) END::FLOAT AS emp_length_yrs,
  home_ownership, verification_status, purpose
FROM a
WHERE trim(term) = '36 months' AND application_type = 'Individual' AND loan_status NOT LIKE 'Does not meet%'
  AND issue_dt >= DATE '2009-01-01'
ORDER BY file_row_number
"""
con = duckdb.connect()
con.execute("SET memory_limit='4GB'; SET threads=4;")
df = con.execute(sql).df()
df["issue_dt"] = pd.to_datetime(df["issue_dt"])

# frozen M2 score
booster = lgb.Booster(model_file=str(ART / "lgbm.txt"))
pm2, _ = score(booster, df, FEATURES, CATEGORICAL, load_categories(ART / "lgbm_cats.json"))
df["pd_m2"] = pm2.astype(np.float32)
df["lp"] = np.log(df.pd_m2 / (1 - df.pd_m2)).astype(np.float32)

# event coding (prereg §A) — tested helper (tests/test_riskutils.py::test_code_events)
T, y = code_events(df.loan_status.to_numpy(), df.lp_mob, df.default_mob, df.W)
df["T"], df["event"] = T, y
df = df[df.W >= 1].reset_index(drop=True)
keep = ["id", "issue_dt", "yr", "issue_q", "loan_status", "addr_state", "grade", "sub_grade", "bad", "lp_mob", "default_mob",
        "W", "T", "event", "funded_amnt", "int_rate", "installment", "total_rec_prncp", "recoveries",
        "collection_recovery_fee", "total_pymnt", "pd_m2", "lp"] + FEATURES
df[keep].to_parquet(OUT)
print(df.groupby("yr").agg(n=("event", "size"), default=("event", lambda s: (s == 1).mean()),
                           prepay=("event", lambda s: (s == 2).mean()), mean_T=("T", "mean")).round(3).to_string())
print(len(df), "loans ->", OUT)
