import numpy as np
import pandas as pd
import pytest
from scipy.stats import ks_2samp
from sklearn.metrics import roc_auc_score

from hazard import cif, expand, fit_mnl
from metrics import Disc, calib_slope, psi
from woe import fit_categorical, fit_numeric

rng = np.random.default_rng(0)


# ---------------------------------------------------------------- PSI / CSI
def test_psi_identical_is_zero():
    assert psi([10, 20, 30], [1, 2, 3]) == pytest.approx(0.0)


def test_psi_known_value():
    e, a = np.array([0.5, 0.5]), np.array([0.6, 0.4])
    exp = (0.6 - 0.5) * np.log(0.6 / 0.5) + (0.4 - 0.5) * np.log(0.4 / 0.5)
    assert psi(e * 1000, a * 1000) == pytest.approx(exp)


def test_psi_empty_bin_is_finite_and_large():
    v = psi([50, 50, 0], [40, 40, 20])
    assert np.isfinite(v) and v > 0.25


def test_csi_of_reference_against_itself_is_zero():
    x = pd.Series(rng.normal(size=5000))
    y = pd.Series((rng.random(5000) < 1 / (1 + np.exp(-x))).astype(float))
    b = fit_numeric("x", x, y)
    counts = b.assign(x).value_counts().reindex(b.labels).fillna(0).to_numpy()
    assert psi(counts, counts) == pytest.approx(0.0)


# ---------------------------------------------------------------- AUC / KS / calibration
def test_disc_matches_sklearn_and_scipy_with_ties():
    s = np.round(rng.normal(size=4000), 1)                      # many ties
    y = (rng.random(4000) < 1 / (1 + np.exp(-s))).astype(float)
    auc, ks = Disc(s, y).auc_ks()
    assert auc == pytest.approx(roc_auc_score(y, s), abs=1e-12)
    assert ks == pytest.approx(ks_2samp(s[y == 1], s[y == 0]).statistic, abs=1e-12)


def test_disc_integer_weights_equal_row_duplication():
    s = rng.normal(size=500)
    y = (rng.random(500) < 0.3).astype(float)
    w = rng.integers(0, 4, 500).astype(float)
    auc_w, ks_w = Disc(s, y).auc_ks(w)
    idx = np.repeat(np.arange(500), w.astype(int))
    auc_r, ks_r = Disc(s[idx], y[idx]).auc_ks()
    assert auc_w == pytest.approx(auc_r) and ks_w == pytest.approx(ks_r)


def test_calibration_slope_on_calibrated_data():
    p = rng.uniform(0.02, 0.5, 200_000)
    y = (rng.random(200_000) < p).astype(float)
    a, b = calib_slope(p, y)
    assert a == pytest.approx(0.0, abs=0.05) and b == pytest.approx(1.0, abs=0.05)


# ---------------------------------------------------------------- WoE binning
def _toy(n=20_000, miss=0.02):
    x = rng.normal(size=n)
    y = (rng.random(n) < 1 / (1 + np.exp(1.5 + 0.8 * x))).astype(float)   # risk decreases with x
    xs = pd.Series(x)
    xs[rng.random(n) < miss] = np.nan
    return xs, pd.Series(y)


def test_woe_numeric_monotone_min_share_missing_bin():
    x, y = _toy()
    b = fit_numeric("x", x, y)
    t = b.table.set_index("bin")
    nonmiss = [lab for lab in b.labels if lab != "MISSING"]
    rates = t.loc[nonmiss, "bad_rate"].to_numpy()
    assert np.all(np.diff(rates) < 0)                       # strictly monotone in the Spearman direction
    assert (t.loc[nonmiss, "pct_n"] / t.loc[nonmiss, "pct_n"].sum() >= 0.05 - 1e-9).all() or len(nonmiss) == 1
    assert "MISSING" in b.labels                            # 2% missing >= 0.5% -> own bin
    woe = t.loc[nonmiss, "woe"].to_numpy()
    assert np.all(np.diff(woe) > 0)                         # lower bad rate -> higher WoE (ln good/bad)


def test_woe_rare_missing_joins_closest_bin():
    x, y = _toy(miss=0.002)
    b = fit_numeric("x", x, y)
    assert "MISSING" not in b.labels and b.missing_to in b.labels


def test_woe_right_closed_boundaries():
    x, y = _toy(miss=0.0)
    b = fit_numeric("x", x, y)
    c0 = b.cuts[0]
    assert b.assign(pd.Series([c0])).iloc[0] == b.labels_num[0]
    assert b.assign(pd.Series([np.nextafter(c0, np.inf)])).iloc[0] == b.labels_num[1]


def test_iv_formula():
    x, y = _toy()
    b = fit_numeric("x", x, y)
    t = b.table
    g = (t.good + 0.5) / (t.good.sum() + 0.5)
    bd = (t.bad + 0.5) / (t.bad.sum() + 0.5)
    assert b.iv == pytest.approx(((g - bd) * np.log(g / bd)).sum())


def test_woe_categorical_rare_and_unseen():
    x = pd.Series(["a"] * 600 + ["b"] * 395 + ["c"] * 5)
    y = pd.Series(([0, 1] * 300) + ([0, 0, 0, 1, 0] * 79) + [1] * 5, dtype=float)
    b = fit_categorical("x", x, y)
    assert b.cat_map["c"] == "OTHER"
    assert b.transform(pd.Series(["zzz"])).iloc[0] == pytest.approx(b.woe["OTHER"])


# ---------------------------------------------------------------- hazard panel / CIF
def test_expand_panel():
    loans = pd.DataFrame({"T": [3, 1, 2], "event": [1, 2, 0]})
    idx, t, y, w = expand(loans)
    assert idx.tolist() == [0, 0, 0, 1, 2, 2]
    assert t.tolist() == [1, 2, 3, 1, 1, 2]
    assert y.tolist() == [0, 0, 1, 2, 0, 0]
    assert w.tolist() == [1.0] * 6


def test_cif_identity():
    hd = np.full((2, 36), 0.01, np.float32)
    hp = np.full((2, 36), 0.03, np.float32)
    s_prev, md, C = cif(hd, hp)
    surv_end = s_prev[:, -1] * (1 - hd[:, -1] - hp[:, -1])
    cif_p = np.cumsum(s_prev * hp, axis=1)[:, -1]
    assert np.allclose(surv_end + C[:, -1] + cif_p, 1.0, atol=1e-5)
    naive = 1 - np.prod(1 - hd, axis=1)
    assert np.all(naive > C[:, -1])                         # ignoring prepayment overstates lifetime PD


def test_fit_mnl_recovers_parameters():
    n = 200_000
    X = np.column_stack([np.ones(n), rng.normal(size=n)])
    B = np.array([[-3.0, -2.0], [0.7, -0.4]])
    eta = X @ B
    P = np.exp(eta) / (1 + np.exp(eta).sum(1, keepdims=True))
    u = rng.random(n)
    y = np.where(u < P[:, 0], 1, np.where(u < P[:, 0] + P[:, 1], 2, 0))
    Bh, _, _ = fit_mnl(X, y, np.ones(n))
    assert np.allclose(Bh, B, atol=0.06)
