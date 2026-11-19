import numpy as np
import pandas as pd
import pytest

from riskutils import (ae_ratio, annuity_schedule, code_events, default_by_mob, lgd_ead_at_default,
                       observable_mob)


# ---------------------------------------------------------------- nullable integers (bug found in overlay.py)
def test_default_by_mob_nullable_int64():
    s = pd.Series([3, 12, 13, None, None], dtype="Int64")
    assert default_by_mob(s, 12).tolist() == [1.0, 1.0, 0.0, 0.0, 0.0]
    assert default_by_mob(s, 12).mean() == pytest.approx(0.4)


def test_naive_nullable_comparison_is_wrong():
    """Documents the pitfall: comparison on Int64 keeps <NA>; mean() then silently drops non-defaulted loans."""
    s = pd.Series([3, 12, 13, None, None], dtype="Int64")
    naive = (s <= 12).astype(float).mean()
    assert naive == pytest.approx(2 / 3)          # wrong denominator (3 defaulted loans only)
    assert default_by_mob(s, 12).mean() != naive


def test_default_by_mob_float_nan_and_boundary():
    a = np.array([np.nan, 6.0, 7.0])
    assert default_by_mob(a, 6).tolist() == [0.0, 1.0, 0.0]


# ---------------------------------------------------------------- censoring / maturity coding
@pytest.mark.parametrize("status,lp,dmob,W,exp", [
    ("Charged Off", 9, 10, 36, (10, 1)),        # default inside window
    ("Charged Off", 29, 30, 20, (20, 0)),       # default after window -> censored at W
    ("Default", 4, 5, 36, (5, 1)),
    ("Fully Paid", 12, None, 36, (12, 2)),      # prepay
    ("Fully Paid", 33, None, 36, (33, 2)),      # boundary: 3 months early = prepay
    ("Fully Paid", 34, None, 36, (34, 0)),      # matured normally -> censored at payoff
    ("Fully Paid", 36, None, 36, (36, 0)),
    ("Fully Paid", 0, None, 36, (1, 2)),        # paid in month 0 -> month 1 prepay
    ("Fully Paid", 25, None, 20, (20, 0)),      # payoff after window -> censored at W
    ("Current", 20, None, 24, (24, 0)),
    ("Late (31-120 days)", 15, None, 18, (18, 0)),
    ("Fully Paid", None, None, 30, (30, 0)),    # no last payment date -> censored at W (never observed)
])
def test_code_events(status, lp, dmob, W, exp):
    T, ev = code_events([status], pd.Series([lp], dtype="Int64"), pd.Series([dmob], dtype="Int64"), [W])
    assert (T[0], int(ev[0])) == exp


# ---------------------------------------------------------------- EAD / LGD
def test_annuity_known_payment_and_amortisation():
    pmt, bal = annuity_schedule([10_000.0], [12.0], 36)
    assert pmt[0] == pytest.approx(332.143, abs=1e-3)
    assert bal[0, 0] == pytest.approx(10_000.0)
    r = 0.01
    assert bal[0, 1] == pytest.approx(10_000 * (1 + r) - pmt[0])          # one payment later
    assert bal[0, -1] * (1 + r) - pmt[0] == pytest.approx(0.0, abs=1e-6)  # last payment clears the loan
    assert np.all(np.diff(bal[0]) < 0)


def test_lgd_formula_and_clipping():
    lgd, ead = lgd_ead_at_default([10_000, 10_000, 10_000, 5_000], [4_000, 4_000, 4_000, 5_000],
                                  [1_200, 0, 9_000, 0], [200, 100, 0, 0])
    assert ead.tolist() == [6_000, 6_000, 6_000, 0]
    assert lgd[0] == pytest.approx(1 - 1_000 / 6_000)
    assert lgd[1] == 1.0          # fee > recovery -> clipped at 1
    assert lgd[2] == 0.0          # recovery > EAD -> clipped at 0
    assert np.isnan(lgd[3])       # no exposure


# ---------------------------------------------------------------- observability / A/E
def test_observable_mob():
    q = pd.Series(pd.to_datetime(["2016-09-01", "2018-09-01", "2012-12-01"]))
    assert observable_mob(q, "2018-09-01").tolist() == [24, 0, 36]


def test_ae_by_mob_simple():
    dmob = pd.Series([3, 10, 14, None, None, None, None, None, None, None], dtype="Int64")
    expected_cif12 = np.full(10, 0.1)               # model expects 10% by MOB 12
    act = default_by_mob(dmob, 12).sum()            # 2 loans
    assert ae_ratio(act, expected_cif12.sum()) == pytest.approx(2.0)
