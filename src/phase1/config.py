"""Phase 1 configuration — mirrors notes/02_prereg_phase1.md (pre-registered 2026-11-19, commit 652b889)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INTERIM = ROOT / "data" / "interim"
ACC = INTERIM / "accepted_2007_to_2018Q4.parquet"
BASE = INTERIM / "p1_base.parquet"          # row-level, git-ignored
ART = INTERIM / "p1"                        # row-level artefacts (scores, models), git-ignored
REP = ROOT / "reports" / "phase1"           # aggregates only
FIG = ROOT / "reports" / "figures"

TRAIN = ("2012-09-01", "2013-12-01")
VALID = ("2014-01-01", "2014-12-01")
OOT = ("2015-01-01", "2015-12-01")
ASOF = "2019-03-01"
CHARGEOFF_LAG_M = 6
SEED = 20261119
B_BOOT = 500

NUMERIC = [
    "loan_amnt", "annual_inc", "dti", "delinq_2yrs", "inq_last_6mths", "mths_since_last_delinq",
    "mths_since_last_record", "open_acc", "pub_rec", "revol_bal", "revol_util", "total_acc",
    "collections_12_mths_ex_med", "mths_since_last_major_derog", "acc_now_delinq", "tot_coll_amt", "tot_cur_bal",
    "total_rev_hi_lim", "acc_open_past_24mths", "avg_cur_bal", "bc_open_to_buy", "bc_util",
    "chargeoff_within_12_mths", "delinq_amnt", "mo_sin_old_il_acct", "mo_sin_old_rev_tl_op", "mo_sin_rcnt_rev_tl_op",
    "mo_sin_rcnt_tl", "mort_acc", "mths_since_recent_bc", "mths_since_recent_bc_dlq", "mths_since_recent_inq",
    "mths_since_recent_revol_delinq", "num_accts_ever_120_pd", "num_actv_bc_tl", "num_actv_rev_tl", "num_bc_sats",
    "num_bc_tl", "num_il_tl", "num_op_rev_tl", "num_rev_accts", "num_rev_tl_bal_gt_0", "num_sats",
    "num_tl_120dpd_2m", "num_tl_30dpd", "num_tl_90g_dpd_24m", "num_tl_op_past_12m", "pct_tl_nvr_dlq",
    "percent_bc_gt_75", "pub_rec_bankruptcies", "tax_liens", "tot_hi_cred_lim", "total_bal_ex_mort",
    "total_bc_limit", "total_il_high_credit_limit",
]
DERIVED = ["fico", "credit_hist_months", "loan_to_income", "emp_length_yrs"]
CATEGORICAL = ["home_ownership", "verification_status", "purpose"]
FEATURES = NUMERIC + DERIVED + CATEGORICAL

MONO_DEC = [  # higher value -> lower risk (-1)
    "fico", "annual_inc", "credit_hist_months", "mths_since_recent_inq", "mths_since_last_delinq",
    "mths_since_last_record", "mths_since_recent_bc", "mort_acc", "pct_tl_nvr_dlq", "bc_open_to_buy",
    "tot_hi_cred_lim", "total_rev_hi_lim", "mo_sin_old_rev_tl_op", "mo_sin_old_il_acct", "mo_sin_rcnt_rev_tl_op",
    "mo_sin_rcnt_tl", "emp_length_yrs",
]
MONO_INC = [  # higher value -> higher risk (+1)
    "dti", "loan_to_income", "inq_last_6mths", "revol_util", "bc_util", "percent_bc_gt_75", "delinq_2yrs", "pub_rec",
    "pub_rec_bankruptcies", "acc_open_past_24mths", "num_tl_op_past_12m", "num_tl_90g_dpd_24m",
    "num_accts_ever_120_pd", "tax_liens", "collections_12_mths_ex_med", "acc_now_delinq", "chargeoff_within_12_mths",
]

# scorecard scaling
PDO, BASE_SCORE, BASE_ODDS = 20, 600, 50
BAD_RATE_TARGET = 0.11   # primary cutoff rule on validation


def load_base(columns=None):
    import pandas as pd
    df = pd.read_parquet(BASE, columns=columns)
    if "issue_dt" in df:
        df["issue_dt"] = pd.to_datetime(df["issue_dt"])
    return df


def split_mask(df, window):
    import pandas as pd
    return (df.issue_dt >= pd.Timestamp(window[0])) & (df.issue_dt <= pd.Timestamp(window[1]))
