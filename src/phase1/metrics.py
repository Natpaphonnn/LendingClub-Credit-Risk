"""Discrimination / calibration metrics with fast bootstrap (pre-registered §5).

Scores: higher = riskier (PD-like) for all functions here.
Bootstrap = resample rows with replacement -> integer weights; AUC/KS computed exactly from weighted counts over
unique score values (ties handled as 0.5), O(n) per replicate.
"""
import numpy as np


class Disc:
    """Precompute sort structure for a (score, y) pair so weighted AUC/KS are O(n)."""

    def __init__(self, score, y):
        self.y = np.asarray(y, dtype=float)
        u, self.inv = np.unique(np.asarray(score, dtype=float), return_inverse=True)
        self.k = len(u)

    def auc_ks(self, w=None):
        w = np.ones_like(self.y) if w is None else w
        b = np.bincount(self.inv, weights=w * self.y, minlength=self.k)
        g = np.bincount(self.inv, weights=w * (1 - self.y), minlength=self.k)
        B, G = b.sum(), g.sum()
        cg = np.cumsum(g) - g            # goods strictly below
        auc = (b * (cg + 0.5 * g)).sum() / (B * G)
        ks = np.max(np.abs(np.cumsum(b) / B - np.cumsum(g) / G))
        return auc, ks


def calib_slope(p, y, w=None, iters=25):
    """Weighted logistic fit y ~ a + b*logit(p); returns (a, b). Newton-Raphson on 2 params."""
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    x = np.log(p / (1 - p))
    y = np.asarray(y, float)
    w = np.ones_like(y) if w is None else w
    beta = np.array([0.0, 1.0])
    X = np.column_stack([np.ones_like(x), x])
    for _ in range(iters):
        eta = X @ beta
        mu = 1 / (1 + np.exp(-eta))
        grad = X.T @ (w * (y - mu))
        H = (X * (w * mu * (1 - mu))[:, None]).T @ X
        step = np.linalg.solve(H, grad)
        beta += step
        if np.abs(step).max() < 1e-8:
            break
    return beta


def point_metrics(pd_, y, w=None):
    pd_ = np.clip(np.asarray(pd_, float), 1e-6, 1 - 1e-6)
    y = np.asarray(y, float)
    w = np.ones_like(y) if w is None else w
    W = w.sum()
    return {
        "mean_pd": (w * pd_).sum() / W,
        "bad_rate": (w * y).sum() / W,
        "citl": (w * (pd_ - y)).sum() / W,
        "brier": (w * (pd_ - y) ** 2).sum() / W,
        "logloss": -(w * (y * np.log(pd_) + (1 - y) * np.log(1 - pd_))).sum() / W,
    }


def evaluate(models: dict, y, pds: dict, B=500, seed=0, slope=True):
    """models: name -> risk score (higher = riskier); pds: name -> PD (or None if not calibrated, e.g. benchmark).
    Returns dict of point estimates + 95% CIs and paired bootstrap samples of Gini."""
    y = np.asarray(y, float)
    n = len(y)
    rng = np.random.default_rng(seed)
    disc = {m: Disc(s, y) for m, s in models.items()}
    out = {m: {} for m in models}
    samples = {m: {"gini": [], "ks": [], "citl": [], "brier": [], "logloss": [], "slope": []} for m in models}
    for m in models:
        auc, ks = disc[m].auc_ks()
        out[m]["gini"], out[m]["ks"] = 2 * auc - 1, ks
        if pds.get(m) is not None:
            out[m].update(point_metrics(pds[m], y))
            out[m]["slope"] = calib_slope(pds[m], y)[1]
    for _ in range(B):
        w = np.bincount(rng.integers(0, n, n), minlength=n).astype(float)
        for m in models:
            auc, ks = disc[m].auc_ks(w)
            samples[m]["gini"].append(2 * auc - 1)
            samples[m]["ks"].append(ks)
            if pds.get(m) is not None:
                pm = point_metrics(pds[m], y, w)
                for k in ("citl", "brier", "logloss"):
                    samples[m][k].append(pm[k])
                if slope:
                    samples[m]["slope"].append(calib_slope(pds[m], y, w, iters=8)[1])
    for m in models:
        for k, v in samples[m].items():
            if v:
                out[m][k + "_lo"], out[m][k + "_hi"] = np.percentile(v, [2.5, 97.5])
    return out, samples


def decile_table(pd_, y, n=10):
    import pandas as pd
    df = pd.DataFrame({"pd": pd_, "y": y})
    df["decile"] = pd.qcut(df["pd"].rank(method="first"), n, labels=False) + 1
    t = df.groupby("decile").agg(n=("y", "size"), mean_pd=("pd", "mean"), bad_rate=("y", "mean")).reset_index()
    return t


def psi(ref_counts, cur_counts, eps=1e-6):
    a = np.asarray(cur_counts, float)
    e = np.asarray(ref_counts, float)
    a, e = a / a.sum(), e / e.sum()
    a, e = np.maximum(a, eps), np.maximum(e, eps)
    return float(((a - e) * np.log(a / e)).sum())
