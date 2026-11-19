"""Phase 0 data audit (steps 2-7 of notes/00_plan.md). Aggregates only — writes markdown tables to reports/audit/.

Usage:  nice -n 19 .venv/bin/python -I src/audit/run_audit.py <interim_dir> <dictionary_xlsx> <out_dir>
"""
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from leakage_map import classify  # noqa: E402

interim, dict_xlsx, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
ACC = interim / "accepted_2007_to_2018Q4.parquet"
REJ = interim / "rejected_2007_to_2018Q4.parquet"

con = duckdb.connect()
con.execute("SET memory_limit='4GB'; SET threads=4;")

sections = []


def q(sql):
    return con.execute(sql).df()


def emit(title, df_or_text, note=None):
    body = df_or_text if isinstance(df_or_text, str) else df_or_text.to_markdown(index=False)
    sections.append(f"## {title}\n\n" + (f"{note}\n\n" if note else "") + body + "\n")
    print(f"\n### {title}\n{body[:3000]}")


# ---------------------------------------------------------------- base view
con.execute(f"""
CREATE VIEW acc AS
SELECT *,
  strptime(issue_d, '%b-%Y')::DATE AS issue_dt,
  year(strptime(issue_d, '%b-%Y')) AS yr,
  TRY_CAST(trim(regexp_replace(term, '[^0-9]', '', 'g')) AS INT) AS term_m,
  TRY_CAST(int_rate AS DOUBLE) AS rate,
  TRY_CAST(fico_range_low AS DOUBLE) AS fico,
  TRY_CAST(loan_amnt AS DOUBLE) AS amt,
  TRY_STRPTIME(last_pymnt_d, '%b-%Y')::DATE AS last_pay_dt
FROM '{ACC}'
WHERE issue_d IS NOT NULL AND TRY_STRPTIME(issue_d, '%b-%Y') IS NOT NULL
""")

raw_n = con.execute(f"SELECT count(*) FROM '{ACC}'").fetchone()[0]
n = con.execute("SELECT count(*) FROM acc").fetchone()[0]
dups = con.execute("SELECT count(*) - count(DISTINCT id) FROM acc").fetchone()[0]
cols = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM '{ACC}'").fetchall()]
rng = con.execute("SELECT min(issue_dt), max(issue_dt) FROM acc").fetchone()
asof = con.execute("""SELECT max(last_pay_dt), max(TRY_STRPTIME(last_credit_pull_d, '%b-%Y')::DATE),
                             max(TRY_STRPTIME(next_pymnt_d, '%b-%Y')::DATE) FROM acc""").fetchone()
member_null = con.execute("SELECT avg((member_id IS NULL)::INT) FROM acc").fetchone()[0]
emit("Accepted file — basics", pd.DataFrame({
    "item": ["rows in file", "rows with valid issue_d (loans)", "dropped (summary/footer rows)", "duplicate ids",
             "columns", "issue_d min", "issue_d max", "max last_pymnt_d (≈ data as-of)", "max last_credit_pull_d",
             "max next_pymnt_d", "member_id null share"],
    "value": [f"{raw_n:,}", f"{n:,}", f"{raw_n-n:,}", dups, len(cols), rng[0], rng[1], asof[0], asof[1], asof[2],
              f"{member_null:.3f}"]}))

emit("Volume by issue year", q("""
SELECT yr, count(*) AS loans, round(sum(amt)/1e6,1) AS funded_musd,
       round(avg((term_m=60)::INT),3) AS share_60m, round(avg(rate),2) AS avg_int_rate
FROM acc GROUP BY yr ORDER BY yr"""))

emit("loan_status — overall", q("""
SELECT loan_status, count(*) AS n, round(100.0*count(*)/sum(count(*)) OVER (),2) AS pct
FROM acc GROUP BY 1 ORDER BY n DESC"""))

st = q("SELECT yr, loan_status, count(*) n FROM acc GROUP BY 1,2")
emit("loan_status × issue year (counts)", st.pivot(index="loan_status", columns="yr", values="n").fillna(0)
     .astype(int).reset_index())

emit("term × issue year", q("SELECT term, yr, count(*) n FROM acc GROUP BY 1,2").pivot(
    index="term", columns="yr", values="n").fillna(0).astype(int).reset_index())

# ---------------------------------------------------------------- data dictionary
dd = pd.read_excel(dict_xlsx, sheet_name=None)
print("dictionary sheets:", {k: v.shape for k, v in dd.items()})
ls = dd[[k for k in dd if "loan" in k.lower()][0]]
ls.columns = ["name", "description"] + list(ls.columns[2:])
ls = ls.dropna(subset=["name"])
ls["key"] = ls["name"].astype(str).str.strip().str.lower()
desc_map = dict(zip(ls["key"], ls["description"].astype(str).str.replace("\n", " ").str.strip()))
# a few known spelling differences between the dictionary and the file
alias = {"verification_status_joint": "verified_status_joint"}

# ---------------------------------------------------------------- missingness by vintage
years = [r[0] for r in con.execute("SELECT DISTINCT yr FROM acc ORDER BY 1").fetchall()]
null_exprs = ", ".join(
    f"round(100*avg((\"{c}\" IS NULL OR trim(\"{c}\")='')::INT),1) AS \"{c}\"" for c in cols)
miss = q(f"SELECT yr, {null_exprs} FROM acc GROUP BY yr ORDER BY yr").set_index("yr").T
miss.columns = [str(c) for c in miss.columns]
miss["all"] = q(f"SELECT {null_exprs} FROM acc").T[0].values
lk = classify()
unmapped = [c for c in cols if c not in lk]
miss.insert(0, "class", [lk.get(c, ("??", ""))[0] for c in miss.index])
miss = miss.reset_index().rename(columns={"index": "column"})

# column catalogue: class + dictionary meaning + overall missing + first year with <50% missing
first_yr = []
for _, r in miss.iterrows():
    ok = [y for y in map(str, years) if r[y] < 50]
    first_yr.append(ok[0] if ok else "never")
cat = pd.DataFrame({
    "column": miss["column"], "class": miss["class"],
    "leak_note": [lk.get(c, ("", ""))[1] for c in miss["column"]],
    "missing_all_%": miss["all"], "first_year_<50%_missing": first_yr,
    "dictionary_meaning": [desc_map.get(alias.get(c, c), "(not in dictionary)")[:160] for c in miss["column"]],
})
(out / "column_catalogue.md").write_text(
    "# Accepted file — column catalogue (class, missingness, LC dictionary meaning)\n\n"
    "Class legend: ID / TIME / TARGET / APP (application-time) / LC (LendingClub decision or pricing output) / "
    "POST (post-origination — leakage for application models). Dictionary: LCDataDictionary.xlsx (Figshare copy, "
    "CC BY 4.0, doi:10.6084/m9.figshare.20016077.v1).\n\n" + cat.to_markdown(index=False) + "\n")
(out / "missingness_by_year.md").write_text(
    "# Accepted file — % missing (null or blank) by issue year\n\n" + miss.to_markdown(index=False) + "\n")
emit("Leakage map — counts by class", cat.groupby("class").size().rename("n_columns").reset_index(),
     f"Unmapped columns: {unmapped or 'none'}. Full table: reports/audit/column_catalogue.md")

# ---------------------------------------------------------------- matured-vintage check
FINAL = "('Fully Paid','Charged Off','Does not meet the credit policy. Status:Fully Paid'," \
        "'Does not meet the credit policy. Status:Charged Off')"
BAD = "('Charged Off','Does not meet the credit policy. Status:Charged Off','Default')"
mat = q(f"""
SELECT yr, term_m, count(*) AS n,
  round(100*avg((loan_status IN {FINAL})::INT),1) AS pct_final,
  round(100*avg((loan_status='Current')::INT),1) AS pct_current,
  round(100*avg((loan_status LIKE 'Late%' OR loan_status IN ('In Grace Period','Default'))::INT),2) AS pct_late_or_default,
  round(100*avg(CASE WHEN loan_status IN {FINAL} THEN (loan_status LIKE '%Charged Off')::INT END),1) AS bad_rate_among_final,
  round(100*avg((loan_status IN {BAD} OR loan_status LIKE 'Late (31%')::INT),1) AS bad_rate_all_loans_lowerbound,
  max(issue_dt + to_months(term_m)) AS last_scheduled_maturity
FROM acc GROUP BY 1,2 ORDER BY 2,1""")
emit("Matured-vintage check: issue year × term", mat,
     "pct_final = Fully Paid or Charged Off (incl. 'does not meet credit policy' variants). "
     "bad_rate_among_final is biased if pct_final < ~98% (early resolutions over-represent both defaults and prepayments). "
     "bad_rate_all_loans_lowerbound counts Charged Off/Default/Late 31-120 over all loans (Current treated as good).")

# quarterly resolution share for the boundary years
emit("Matured check by issue quarter (2014-2016, both terms)", q(f"""
SELECT year(issue_dt) AS yr, quarter(issue_dt) AS q, term_m, count(*) n,
  round(100*avg((loan_status IN {FINAL})::INT),1) AS pct_final,
  round(100*avg(CASE WHEN loan_status IN {FINAL} THEN (loan_status LIKE '%Charged Off')::INT END),1) AS bad_among_final
FROM acc WHERE yr BETWEEN 2014 AND 2016 GROUP BY 1,2,3 ORDER BY 3,1,2"""))

# ---------------------------------------------------------------- policy_code / credit-policy flags
emit("policy_code and 'does not meet credit policy' by year", q("""
SELECT yr, policy_code, count(*) n,
  sum((loan_status LIKE 'Does not meet%')::INT) AS not_meet_policy
FROM acc GROUP BY 1,2 ORDER BY 1,2"""))

# ---------------------------------------------------------------- G: cutoffs / discontinuities
emit("G1. FICO (fico_range_low) floor by year and share at the floor", q("""
SELECT yr, min(fico) AS fico_min, round(100*avg((fico<660)::INT),2) AS pct_below_660,
  round(100*avg((fico BETWEEN 660 AND 664)::INT),2) AS pct_660_664, count(DISTINCT fico) AS n_bins,
  round(avg(TRY_CAST(fico_range_high AS DOUBLE)-fico),1) AS bin_width
FROM acc GROUP BY yr ORDER BY yr"""))

con.execute("""CREATE TEMP TABLE g AS
WITH b AS (SELECT CASE WHEN yr<=2009 THEN '2007-09' WHEN yr<=2012 THEN '2010-12' WHEN yr<=2015 THEN '2013-15' ELSE '2016-18' END AS era,
                  fico, sub_grade, rate FROM acc WHERE fico BETWEEN 640 AND 800),
c AS (SELECT era, fico, sub_grade, count(*) k FROM b GROUP BY 1,2,3),
m AS (SELECT era, fico, arg_max(sub_grade, k * 1000 - rank_sg) AS modal_subgrade, max(k) AS kmax
      FROM (SELECT *, dense_rank() OVER (PARTITION BY era, fico ORDER BY sub_grade) AS rank_sg FROM c) GROUP BY 1,2)
SELECT b.era, b.fico, count(*) n, avg(rate) AS mean_rate, any_value(m.modal_subgrade) AS modal_subgrade,
       any_value(m.kmax) / count(*) AS share_modal
FROM b JOIN m USING (era, fico) GROUP BY 1,2""")  # deterministic mode: most frequent, ties -> alphabetically first
g = q("SELECT * FROM g ORDER BY era, fico")
g["jump_vs_prev_bin_pp"] = g.groupby("era")["mean_rate"].diff().round(2)
g["mean_rate"] = g["mean_rate"].round(2)
g["share_modal"] = (100 * g["share_modal"]).round(1)
(out / "fico_rate_profile.md").write_text("# Mean int_rate and modal sub_grade by FICO bin and era\n\n"
                                          + g.to_markdown(index=False) + "\n")
big = g[g["n"] >= 200].copy()
big["abs_jump"] = big["jump_vs_prev_bin_pp"].abs()
base = big.groupby("era")["abs_jump"].median().round(2).rename("median_abs_jump_pp").reset_index()
emit("G2a. Typical (median) mean-rate change between adjacent FICO bins, by era", base)
emit("G2. Largest mean-int_rate jumps between adjacent 5-pt FICO bins (bins with n≥200)",
     big.sort_values("abs_jump", ascending=False).groupby("era").head(4)[
         ["era", "fico", "n", "mean_rate", "jump_vs_prev_bin_pp", "modal_subgrade", "share_modal"]],
     "Full profile: reports/audit/fico_rate_profile.md. share_modal = % of loans in the bin that get the bin's modal "
     "sub_grade (100% would mean a deterministic FICO→grade map = sharp RD).")

emit("G3. How much of int_rate is explained by FICO bin vs sub_grade (within issue month)", q("""
WITH b AS (SELECT issue_d, fico, sub_grade, rate, yr FROM acc WHERE rate IS NOT NULL AND fico IS NOT NULL),
f AS (SELECT *, avg(rate) OVER (PARTITION BY issue_d, fico) AS m_f, avg(rate) OVER (PARTITION BY issue_d, sub_grade) AS m_s,
             avg(rate) OVER (PARTITION BY issue_d) AS m_t FROM b)
SELECT CASE WHEN yr<=2009 THEN '2007-09' WHEN yr<=2012 THEN '2010-12' WHEN yr<=2015 THEN '2013-15' ELSE '2016-18' END AS era,
  count(*) n,
  round(1 - sum((rate-m_f)^2)/sum((rate-m_t)^2),3) AS r2_month_x_ficobin,
  round(1 - sum((rate-m_s)^2)/sum((rate-m_t)^2),3) AS r2_month_x_subgrade
FROM f GROUP BY 1 ORDER BY 1"""),
    "R² of int_rate on cell means (within-month variation only). If sub_grade explains ~100% but FICO much less, "
    "rate is a deterministic function of grade+date, and grade is NOT a sharp function of FICO.")

rp = q("""
WITH rc AS (SELECT sub_grade, issue_dt, rate, count(*) k FROM acc WHERE rate IS NOT NULL GROUP BY 1,2,3),
m AS (SELECT sub_grade, issue_dt, arg_max(rate, k * 1e6 - rate) AS r, sum(k) n, count(*) AS n_rates FROM rc GROUP BY 1,2),
c AS (SELECT *, lag(r) OVER (PARTITION BY sub_grade ORDER BY issue_dt) AS prev_r FROM m)
SELECT year(issue_dt) AS yr, count(DISTINCT CASE WHEN r<>prev_r THEN issue_dt END) AS months_with_any_reprice,
  sum((r<>prev_r)::INT) AS subgrade_month_reprices, round(avg(abs(r-prev_r)) FILTER (WHERE r<>prev_r),2) AS mean_abs_change_pp,
  round(avg(n_rates),2) AS avg_distinct_rates_per_subgrade_month
FROM c GROUP BY 1 ORDER BY 1""")
emit("G4. Repricing events: modal int_rate of a sub_grade changes from one issue month to the next", rp,
     "A repricing date shifts the rate for the same sub-grade (same risk) → candidate natural experiment "
     "(difference-in-discontinuities in time) for the causal rate→default question.")

# ---------------------------------------------------------------- 7: text
emit("7. Text fields — share non-empty by year", q("""
SELECT yr, count(*) n,
  round(100*avg(("desc" IS NOT NULL AND length(trim("desc"))>0)::INT),1) AS pct_desc,
  round(median(CASE WHEN length(trim("desc"))>0 THEN length(regexp_replace("desc",'Borrower added on [0-9/]+ >','','g')) END)) AS desc_median_chars,
  round(100*avg((coalesce(length(trim("desc")),0)>=100)::INT),1) AS pct_desc_ge_100chars,
  round(100*avg((emp_title IS NOT NULL AND length(trim(emp_title))>0)::INT),1) AS pct_emp_title,
  round(100*avg((title IS NOT NULL AND length(trim(title))>0)::INT),1) AS pct_title
FROM acc GROUP BY yr ORDER BY yr"""))
emit("7b. desc present — monthly, 2012-06 to 2014-12", q("""
SELECT strftime(issue_dt,'%Y-%m') AS m, count(*) n, round(100*avg((coalesce(length(trim("desc")),0)>0)::INT),1) AS pct_desc
FROM acc WHERE issue_dt BETWEEN DATE '2012-06-01' AND DATE '2014-12-01' GROUP BY 1 ORDER BY 1"""))
emit("7c. Bad rate among resolved loans: with vs without desc (36m, 2009-2013)", q(f"""
SELECT yr, (coalesce(length(trim("desc")),0)>0) AS has_desc, count(*) n,
  round(100*avg((loan_status LIKE '%Charged Off')::INT),1) AS bad_rate
FROM acc WHERE term_m=36 AND yr BETWEEN 2009 AND 2013 AND loan_status IN {FINAL} GROUP BY 1,2 ORDER BY 1,2"""))

# ---------------------------------------------------------------- evidence for senior items A-D
emit("A. Event timing for survival / competing risks (resolved loans, 36m & 60m)", q(f"""
SELECT term_m,
  CASE WHEN loan_status LIKE '%Charged Off' THEN 'charged off' WHEN loan_status LIKE '%Fully Paid' THEN 'fully paid' END AS outcome,
  count(*) n,
  round(median(date_diff('month', issue_dt, last_pay_dt))) AS median_months_to_last_pay,
  round(100*avg((date_diff('month', issue_dt, last_pay_dt) < term_m - 3)::INT),1) AS pct_resolved_3m_before_maturity,
  round(100*avg((last_pay_dt IS NULL)::INT),2) AS pct_no_last_pay_d
FROM acc WHERE loan_status IN {FINAL} AND yr BETWEEN 2009 AND 2015 GROUP BY 1,2 ORDER BY 1,2"""),
    "For Fully Paid, 'resolved >3m before maturity' = prepayment. For Charged Off, last_pymnt_d gives an approximate "
    "default time (charge-off usually ~4-5 months after last payment). Month-level event times are therefore derivable.")
emit("B. Geographic × time spread (for macro-linked PD with state unemployment)", q("""
SELECT yr, count(DISTINCT addr_state) AS n_states, count(DISTINCT left(zip_code,3)) AS n_zip3,
  round(100*max(cnt)/count(*),1) AS top_state_pct, arg_max(addr_state, cnt) AS top_state
FROM (SELECT yr, addr_state, zip_code, count(*) OVER (PARTITION BY yr, addr_state) AS cnt FROM acc)
GROUP BY yr ORDER BY yr"""))
emit("C. Cash-flow fields for profit / LGD (resolved loans 2009-2015)", q(f"""
SELECT CASE WHEN loan_status LIKE '%Charged Off' THEN 'charged off' ELSE 'fully paid' END AS outcome, count(*) n,
  round(avg(TRY_CAST(total_pymnt AS DOUBLE)/TRY_CAST(funded_amnt AS DOUBLE)),3) AS mean_total_pymnt_over_funded,
  round(avg(TRY_CAST(recoveries AS DOUBLE)/TRY_CAST(funded_amnt AS DOUBLE)),3) AS mean_recoveries_over_funded,
  round(1-avg((TRY_CAST(total_rec_prncp AS DOUBLE)+TRY_CAST(recoveries AS DOUBLE)-TRY_CAST(collection_recovery_fee AS DOUBLE))
        /TRY_CAST(funded_amnt AS DOUBLE)),3) AS approx_LGD_principal
FROM acc WHERE loan_status IN {FINAL} AND yr BETWEEN 2009 AND 2015 GROUP BY 1 ORDER BY 1"""),
    "approx_LGD_principal for fully paid is ~0 by construction; shown as a sanity check.")
emit("D. Grade spread of bad rate (monotonicity sanity, 36m 2010-2015 resolved)", q(f"""
SELECT grade, count(*) n, round(100*avg((loan_status LIKE '%Charged Off')::INT),1) AS bad_rate, round(avg(rate),2) AS avg_rate
FROM acc WHERE term_m=36 AND yr BETWEEN 2010 AND 2015 AND loan_status IN {FINAL} GROUP BY 1 ORDER BY 1"""))

# ---------------------------------------------------------------- rejected file (step 5)
if REJ.exists():
    rcols = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM '{REJ}'").fetchall()]
    con.execute(f"""
    CREATE VIEW rej AS SELECT *,
      TRY_CAST("Application Date" AS DATE) AS app_dt,
      year(TRY_CAST("Application Date" AS DATE)) AS yr,
      TRY_CAST("Risk_Score" AS DOUBLE) AS risk,
      TRY_CAST(regexp_replace("Debt-To-Income Ratio", '%', '') AS DOUBLE) AS dti_r,
      TRY_CAST("Amount Requested" AS DOUBLE) AS amt_r
    FROM '{REJ}'""")
    rn = con.execute("SELECT count(*), min(app_dt), max(app_dt), sum((app_dt IS NULL)::INT) FROM rej").fetchone()
    emit("Rejected file — basics", pd.DataFrame({
        "item": ["rows", "columns", "Application Date min", "max", "unparseable dates"],
        "value": [f"{rn[0]:,}", ", ".join(rcols), rn[1], rn[2], rn[3]]}))
    rnull = ", ".join(f"round(100*avg((\"{c}\" IS NULL OR trim(\"{c}\")='')::INT),1) AS \"{c}\"" for c in rcols)
    emit("Rejected file — % missing by year", q(f"SELECT yr, count(*) AS n, {rnull} FROM rej GROUP BY yr ORDER BY yr"))
    emit("Rejected file — Risk_Score / DTI / amount by year", q("""
    SELECT yr, round(min(risk)) AS risk_min, round(quantile_cont(risk,0.05)) AS risk_p05,
      round(median(risk)) AS risk_p50, round(quantile_cont(risk,0.95)) AS risk_p95, round(max(risk)) AS risk_max,
      round(median(dti_r),1) AS dti_p50, round(100*avg((dti_r>=100)::INT),1) AS pct_dti_ge_100, round(median(amt_r)) AS amt_p50
    FROM rej GROUP BY yr ORDER BY yr"""),
        "LC dictionary: Risk_Score = FICO for applications before 2013-11-05, VantageScore after (scales differ).")
    emit("Accepted vs rejected volume by year (approval-rate proxy)", q("""
    SELECT a.yr, a.accepted, r.rejected, round(100.0*a.accepted/(a.accepted+r.rejected),1) AS pct_accepted
    FROM (SELECT yr, count(*) accepted FROM acc GROUP BY yr) a JOIN (SELECT yr, count(*) rejected FROM rej GROUP BY yr) r
    USING (yr) ORDER BY yr"""),
        "Caveat: the rejected file includes many incomplete/auto-declined applications (e.g. DTI≥100%, missing score), "
        "so this is not a clean approval rate.")
    emit("Accepted file — same fields as rejected, by year (for comparison)", q("""
    SELECT yr, round(median(fico)) AS fico_low_p50, round(min(fico)) AS fico_low_min,
      round(median(TRY_CAST(dti AS DOUBLE)),1) AS dti_p50, round(median(amt)) AS amt_p50
    FROM acc GROUP BY yr ORDER BY yr"""))

(out / "audit_tables.md").write_text(
    "# Phase 0 audit tables (aggregates only — generated by src/audit/run_audit.py)\n\n" + "\n".join(sections))
print("\nwrote", out)
