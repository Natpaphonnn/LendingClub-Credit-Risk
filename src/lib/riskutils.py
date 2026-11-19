"""Small, pure, tested helpers for logic that is easy to get wrong (see tests/).

- default_by_mob: nullable-integer safe "defaulted by month k" indicator (bug found in overlay.py, Phase 3 prep)
- code_events: competing-risk event / censoring coding (notes/03_prereg_phase2.md §A)
- annuity_schedule: EAD = scheduled balance at the start of each month
- lgd_ead_at_default: LGD on exposure at default from recoveries
- observable_mob: last MOB fully observable for an issue quarter given an observation limit
- ae_ratio: actual / expected
"""
import numpy as np
import pandas as pd

NEVER = 999


def as_float(x) -> np.ndarray:
    """Convert a numeric Series / array (incl. pandas nullable Int64 with <NA>) to float64 with NaN."""
    if isinstance(x, pd.Series):
        return x.astype("float64").to_numpy()
    return np.asarray(x, dtype="float64")


def default_by_mob(default_mob, k: int) -> np.ndarray:
    """1.0 if the loan defaulted at or before month-on-book k, else 0.0. Non-defaulted (NaN / <NA>) -> 0.0."""
    d = as_float(default_mob)
    return (np.nan_to_num(d, nan=NEVER) <= k).astype(float)


def code_events(loan_status, lp_mob, default_mob, W, prepay_margin: int = 3, term: int = 36):
    """Competing-risk coding per loan. Returns (T, event) with event 0 = censored, 1 = default, 2 = prepay.

    default : status in {Charged Off, Default} and default_mob <= W            -> T = default_mob
    prepay  : Fully Paid and max(lp_mob, 1) <= min(term - prepay_margin, W)   -> T = max(lp_mob, 1)
    matured : Fully Paid and term - prepay_margin < p <= W                    -> censored at p
    else    : censored at W
    """
    status = np.asarray(loan_status, dtype=object)
    W = as_float(W)
    d = as_float(default_mob)
    p = np.maximum(as_float(lp_mob), 1.0)           # NaN (no last payment) stays NaN -> never prepay -> censored
    T = W.copy()
    ev = np.zeros(len(W), dtype=np.int8)
    is_def = np.isin(status, ["Charged Off", "Default"])
    m_def = is_def & (np.nan_to_num(d, nan=np.inf) <= W)
    T[m_def], ev[m_def] = d[m_def], 1
    is_fp = status == "Fully Paid"
    m_pre = is_fp & (p <= np.minimum(term - prepay_margin, W))
    T[m_pre], ev[m_pre] = p[m_pre], 2
    m_mat = is_fp & (p > term - prepay_margin) & (p <= W)
    T[m_mat] = p[m_mat]
    return T, ev


def annuity_schedule(principal, annual_rate_pct, term: int = 36):
    """Level-payment schedule. Returns (payment (n,), balance at START of month t=1..term (n, term))."""
    P = np.asarray(principal, float)[:, None]
    r = (np.asarray(annual_rate_pct, float) / 1200.0)[:, None]
    t = np.arange(1, term + 1)[None, :]
    pmt = P * r / (1 - (1 + r) ** -term)
    bal = P * (1 + r) ** (t - 1) - pmt * ((1 + r) ** (t - 1) - 1) / r
    return pmt[:, 0], bal


def lgd_ead_at_default(funded, principal_received, recoveries, collection_fee):
    """EAD at default = funded − principal received; LGD = 1 − (recoveries − fee) / EAD, clipped to [0, 1].
    Rows with EAD <= 0 get NaN LGD."""
    ead = np.asarray(funded, float) - np.asarray(principal_received, float)
    net = np.asarray(recoveries, float) - np.asarray(collection_fee, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        lgd = np.where(ead > 0, np.clip(1 - net / ead, 0, 1), np.nan)
    return lgd, ead


def observable_mob(quarter_last_month: pd.Series, limit: str, cap: int = 36) -> np.ndarray:
    """Months on book fully observable for every loan of a quarter: limit − last issue month of the quarter."""
    lim = pd.Timestamp(limit)
    q = pd.to_datetime(quarter_last_month)
    m = (lim.year - q.dt.year) * 12 + (lim.month - q.dt.month)
    return np.minimum(m.to_numpy(), cap)


def ae_ratio(actual_events: float, expected_events: float) -> float:
    return float(actual_events) / float(expected_events)


def payments_due(issue_dt, report_month: str) -> np.ndarray:
    """Number of monthly payments that have fallen due by report_month (payment t is due in issue month + t).
    Loan issued in the report month -> 0. Used for reporting-date staging (bug fixed: previously off by one)."""
    rep = pd.Timestamp(report_month)
    d = pd.to_datetime(pd.Series(issue_dt))
    return ((rep.year - d.dt.year) * 12 + (rep.month - d.dt.month)).to_numpy()
