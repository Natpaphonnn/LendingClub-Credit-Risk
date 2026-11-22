"""Information set of the E2 as-of model (notes/08_prereg_extensions.md §E2; gate round 2 R3-3).

A lender deciding on 2014-12-31 may use a loan's 12-month bad label only once it is knowable: the 12-month window has closed AND a
default inside it would already show as charged off, i.e. at issue month + 12 + CHARGEOFF_LAG_M (6) months ≤ the decision month.
Events themselves (first missed payment, issue month + default_mob) must fall by 2014-06.
"""
import pandas as pd

DECISION = "2014-12-01"                      # decision month (31 Dec 2014)
EVENT_LIMIT = "2014-06-01"                   # last month in which a used default event may occur
TRAIN = ("2012-09-01", "2013-03-01")
VALID = ("2013-04-01", "2013-06-01")
LABEL_MOB = 12


def label_available(issue_dt: pd.Series, lag_m: int) -> pd.Series:
    """Month from which the bad12 label of each loan is knowable (window close + charge-off lag)."""
    return pd.to_datetime(issue_dt).dt.to_period("M").dt.to_timestamp() + pd.DateOffset(months=LABEL_MOB + lag_m)


def event_month(issue_dt: pd.Series, default_mob: pd.Series) -> pd.Series:
    """Month of the first missed payment for defaulted loans (NaT otherwise)."""
    base = pd.to_datetime(issue_dt).dt.to_period("M").dt.to_timestamp()
    d = pd.to_numeric(default_mob, errors="coerce")
    return pd.Series([b + pd.DateOffset(months=int(x)) if pd.notna(x) else pd.NaT for b, x in zip(base, d)], index=base.index)
