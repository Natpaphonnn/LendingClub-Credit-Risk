"""Leakage map for the accepted-loans file: every column -> (class, note).

Classes
  ID     identifiers / links — never a feature
  APP    known at application time (borrower-stated or credit bureau pull at application) — OK for application models
  LC     LendingClub's own decision / pricing / listing outputs, fixed at origination. Not borrower risk inputs:
         int_rate, grade, sub_grade, installment are the *output* of LC's model. Use only as a benchmark or
         policy variable, never as a feature of "our" scorecard (it would just copy LC's score).
  TIME   origination time index (used for splits / vintages, not as a feature)
  TARGET loan_status (label source)
  POST   observed after origination (payments, recoveries, hardship, settlement, refreshed bureau) — leakage for
         application models; usable only for monitoring / survival / LGD / profit evaluation
"""

ID = ["id", "member_id", "url"]
TIME = ["issue_d"]
TARGET = ["loan_status"]

LC = {
    "funded_amnt": "amount LC committed (can be < requested); set at origination",
    "funded_amnt_inv": "amount funded by investors — known only after listing; mild leak, do not use",
    "int_rate": "LC pricing output (function of sub_grade + date)",
    "installment": "derived from funded_amnt, int_rate, term",
    "grade": "LC risk grade (LC model output)",
    "sub_grade": "LC risk sub-grade (LC model output)",
    "initial_list_status": "whole vs fractional listing — LC allocation decision",
    "policy_code": "1 = meets current credit policy, 2 = new products not publicly available",
    "disbursement_method": "cash vs direct-pay; only from 2018",
}

APP_CORE = [
    "loan_amnt", "term", "emp_title", "emp_length", "home_ownership", "annual_inc", "verification_status",
    "desc", "purpose", "title", "zip_code", "addr_state", "dti", "delinq_2yrs", "earliest_cr_line",
    "fico_range_low", "fico_range_high", "inq_last_6mths", "mths_since_last_delinq", "mths_since_last_record",
    "open_acc", "pub_rec", "revol_bal", "revol_util", "total_acc", "collections_12_mths_ex_med",
    "mths_since_last_major_derog", "application_type", "annual_inc_joint", "dti_joint",
    "verification_status_joint", "acc_now_delinq", "tot_coll_amt", "tot_cur_bal", "open_acc_6m", "open_act_il",
    "open_il_12m", "open_il_24m", "mths_since_rcnt_il", "total_bal_il", "il_util", "open_rv_12m", "open_rv_24m",
    "max_bal_bc", "all_util", "total_rev_hi_lim", "inq_fi", "total_cu_tl", "inq_last_12m",
    "acc_open_past_24mths", "avg_cur_bal", "bc_open_to_buy", "bc_util", "chargeoff_within_12_mths",
    "delinq_amnt", "mo_sin_old_il_acct", "mo_sin_old_rev_tl_op", "mo_sin_rcnt_rev_tl_op", "mo_sin_rcnt_tl",
    "mort_acc", "mths_since_recent_bc", "mths_since_recent_bc_dlq", "mths_since_recent_inq",
    "mths_since_recent_revol_delinq", "num_accts_ever_120_pd", "num_actv_bc_tl", "num_actv_rev_tl",
    "num_bc_sats", "num_bc_tl", "num_il_tl", "num_op_rev_tl", "num_rev_accts", "num_rev_tl_bal_gt_0",
    "num_sats", "num_tl_120dpd_2m", "num_tl_30dpd", "num_tl_90g_dpd_24m", "num_tl_op_past_12m",
    "pct_tl_nvr_dlq", "percent_bc_gt_75", "pub_rec_bankruptcies", "tax_liens", "tot_hi_cred_lim",
    "total_bal_ex_mort", "total_bc_limit", "total_il_high_credit_limit", "revol_bal_joint",
    "sec_app_fico_range_low", "sec_app_fico_range_high", "sec_app_earliest_cr_line", "sec_app_inq_last_6mths",
    "sec_app_mort_acc", "sec_app_open_acc", "sec_app_revol_util", "sec_app_open_act_il",
    "sec_app_num_rev_accts", "sec_app_chargeoff_within_12_mths", "sec_app_collections_12_mths_ex_med",
    "sec_app_mths_since_last_major_derog",
]

POST = {
    "pymnt_plan": "payment plan put in place (post)",
    "out_prncp": "outstanding principal at data pull",
    "out_prncp_inv": "outstanding principal (investor share)",
    "total_pymnt": "payments received to date",
    "total_pymnt_inv": "payments received to date (investor share)",
    "total_rec_prncp": "principal received", "total_rec_int": "interest received",
    "total_rec_late_fee": "late fees received", "recoveries": "post charge-off recoveries",
    "collection_recovery_fee": "collection fee", "last_pymnt_d": "last payment month",
    "last_pymnt_amnt": "last payment amount", "next_pymnt_d": "next scheduled payment",
    "last_credit_pull_d": "most recent bureau pull by LC", "last_fico_range_high": "refreshed FICO (post)",
    "last_fico_range_low": "refreshed FICO (post)",
}
for c in ["hardship_flag", "hardship_type", "hardship_reason", "hardship_status", "deferral_term",
          "hardship_amount", "hardship_start_date", "hardship_end_date", "payment_plan_start_date",
          "hardship_length", "hardship_dpd", "hardship_loan_status", "orig_projected_additional_accrued_interest",
          "hardship_payoff_balance_amount", "hardship_last_payment_amount"]:
    POST[c] = "hardship program (post-origination, mostly 2017+ incl. COVID-era not in this file)"
for c in ["debt_settlement_flag", "debt_settlement_flag_date", "settlement_status", "settlement_date",
          "settlement_amount", "settlement_percentage", "settlement_term"]:
    POST[c] = "debt settlement after charge-off (post)"


def classify():
    m = {}
    for c in ID:
        m[c] = ("ID", "identifier / listing URL")
    for c in TIME:
        m[c] = ("TIME", "origination month")
    for c in TARGET:
        m[c] = ("TARGET", "current status at data pull — label source")
    for c, n in LC.items():
        m[c] = ("LC", n)
    for c in APP_CORE:
        m[c] = ("APP", "")
    for c, n in POST.items():
        m[c] = ("POST", n)
    return m
