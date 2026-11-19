"""Build the Phase 1 base table: 36m, Individual, meets credit policy, issued 2012-09..2018-12.

Output (row-level, git-ignored): data/interim/p1_base.parquet
Usage: nice -n 19 .venv/bin/python -I src/phase1/build_dataset.py
"""
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import ACC, ASOF, BASE, NUMERIC  # noqa: E402

num = ",\n  ".join(f"TRY_CAST({c} AS DOUBLE)::FLOAT AS {c}" for c in NUMERIC)
sql = f"""
COPY (
WITH a AS (
  SELECT *, strptime(issue_d, '%b-%Y')::DATE AS issue_dt, TRY_STRPTIME(last_pymnt_d, '%b-%Y')::DATE AS lp_dt
  FROM read_parquet('{ACC}', file_row_number=true)
  WHERE TRY_STRPTIME(issue_d, '%b-%Y') IS NOT NULL
)
SELECT
  TRY_CAST(id AS BIGINT) AS id,
  issue_dt,
  year(issue_dt) AS yr,
  year(issue_dt)::VARCHAR || 'Q' || quarter(issue_dt)::VARCHAR AS issue_q,
  loan_status,
  CASE WHEN loan_status IN ('Charged Off','Default') THEN 1 WHEN loan_status = 'Fully Paid' THEN 0 END::FLOAT AS bad,
  CASE WHEN loan_status IN ('Charged Off','Default')
       THEN coalesce(date_diff('month', issue_dt, lp_dt) + 1, 1) END AS default_mob,
  date_diff('month', issue_dt, DATE '{ASOF}') AS mob_asof,
  grade, sub_grade, TRY_CAST(int_rate AS DOUBLE)::FLOAT AS int_rate, addr_state,
  {num},
  (TRY_CAST(fico_range_low AS DOUBLE) + 2)::FLOAT AS fico,
  date_diff('month', TRY_STRPTIME(earliest_cr_line, '%b-%Y')::DATE, issue_dt)::FLOAT AS credit_hist_months,
  (TRY_CAST(loan_amnt AS DOUBLE) / NULLIF(TRY_CAST(annual_inc AS DOUBLE), 0))::FLOAT AS loan_to_income,
  CASE WHEN emp_length = '< 1 year' THEN 0
       WHEN emp_length = '10+ years' THEN 10
       ELSE TRY_CAST(regexp_extract(emp_length, '^([0-9]+)', 1) AS INT) END::FLOAT AS emp_length_yrs,
  home_ownership, verification_status, purpose
FROM a
WHERE trim(term) = '36 months'
  AND application_type = 'Individual'
  AND loan_status NOT LIKE 'Does not meet%'
  AND issue_dt >= DATE '2012-09-01'
ORDER BY file_row_number
) TO '{BASE}' (FORMAT parquet, COMPRESSION zstd)
"""
con = duckdb.connect()
con.execute("SET memory_limit='4GB'; SET threads=4;")
con.execute(sql)
print(con.execute(f"""SELECT yr, count(*) n, round(avg(bad),4) bad_rate_final, round(avg((bad IS NULL)::INT),4) pct_not_final
                      FROM '{BASE}' GROUP BY 1 ORDER BY 1""").df().to_string())
print(con.execute(f"SELECT count(*) FROM '{BASE}'").fetchone()[0], "rows ->", BASE)
