import numpy as np
import pandas as pd
import pytest

from ecl_lib import ecl_from, pooled_lgd, staging_e4


def test_pooled_lgd_discounting():
    d = pd.DataFrame({"funded_amnt": [10_000.0], "total_rec_prncp": [4_000.0], "recoveries": [1_200.0],
                      "collection_recovery_fee": [200.0], "int_rate": [12.0]})
    u, _, _ = pooled_lgd(d)
    k12, _, _ = pooled_lgd(d, discount_months=12)
    assert u == pytest.approx(1 - 1_000 / 6_000)
    assert k12 == pytest.approx(1 - 1_000 * 1.01 ** -12 / 6_000)
    assert k12 > u                                   # discounting recoveries raises LGD


def test_ead_shift_for_90dpd():
    H = 36
    hd = np.zeros((1, H), np.float32)
    hd[0, 9] = 1.0                                    # certain default at MOB 10
    hp = np.zeros_like(hd)
    EAD = np.arange(H, 0, -1, dtype=float)[None, :]   # 36, 35, ...
    DF = np.ones((1, H))
    e0 = ecl_from(hd, hp, EAD, DF, 1.0, ead_shift=0)
    e2 = ecl_from(hd, hp, EAD, DF, 1.0, ead_shift=2)
    assert e0["el_life_undisc"][0] == EAD[0, 9]
    assert e2["el_life_undisc"][0] == EAD[0, 7]       # 90-DPD event at MOB 10 -> exposure at first missed (MOB 8)


def test_staging_e4_classification():
    """Loans issued 2015-06 (6 instalments due by Dec-2015): first missed at MOB 4 -> m = 3 (stage 3);
    MOB 5 -> m = 2 (stage 2); MOB 7 -> not yet due (stage 1); prepaid at MOB 3 -> derecognised; performing -> stage 1."""
    port = pd.DataFrame({
        "issue_dt": pd.to_datetime(["2015-06-01"] * 5),
        "loan_status": ["Charged Off", "Charged Off", "Charged Off", "Fully Paid", "Current"],
        "default_mob": pd.array([4, 5, 7, None, None], dtype="Int64"),
        "event": [1, 1, 1, 2, 0], "T": [4, 5, 7, 3, 36],
        "int_rate": [12.0] * 5, "funded_amnt": [10_000.0] * 5, "lp": [-2.0] * 5, "loan_amnt": [10_000.0] * 5})

    class Sc:
        def loan_cols(self, d):
            return np.column_stack([d.lp.to_numpy(), np.zeros(len(d)), np.zeros(len(d))])
    B = np.zeros((10, 2))
    B[0] = [-6, -6]
    st = staging_e4(port, {"B": B, "scaler": Sc()}, 0.9, "2015-12-01").set_index("stage")
    counts = st["loans"].to_list()
    assert counts[:4] == [2, 1, 1, 1]                 # stage 1, stage 2, stage 3, derecognised (+ memo row: m >= 6)
    assert counts[4] == 0


def _synthetic_loans(n=6000, seed=3):
    rng = np.random.default_rng(seed)
    months = pd.date_range("2009-01-01", "2014-12-01", freq="MS")
    issue = months[rng.integers(0, len(months), n)]
    u = rng.random(n)
    status = np.where(u < 0.15, "Charged Off", np.where(u < 0.75, "Fully Paid", "Current"))
    return pd.DataFrame({"issue_dt": issue, "loan_status": status,
                         "lp_mob": rng.integers(1, 37, n).astype(float),
                         "default_mob": np.where(status == "Charged Off", rng.integers(1, 37, n), np.nan),
                         "int_rate": rng.uniform(6, 25, n), "loan_amnt": rng.uniform(1e3, 35e3, n), "lp": rng.normal(-2, 0.6, n)})


def test_fit_hazard_asof_censoring_window_and_identifiability():
    """Gate R7-1 / R2-1 / R3-6: outcomes only to R − 6m; the pre-registered 2012-09 start at R = 2014-12 cannot identify MOB 22–36."""
    from ecl_lib import fit_hazard_asof
    from hazard import NotIdentifiedError
    loans = _synthetic_loans()
    with pytest.raises(NotIdentifiedError):
        fit_hazard_asof(loans, "2014-12-31")                       # 2012-09 start: max MOB 21
    m = fit_hazard_asof(loans, "2014-12-31", start="2009-01-01")
    assert m["max_mob_observed"] == 36
    assert m["issue_window"][1] <= "2014-05-01"                     # later issues have no observable month by 2014-06
    m0 = fit_hazard_asof(loans, "2014-12-31", check=False)
    assert m0["max_mob_observed"] == 21
