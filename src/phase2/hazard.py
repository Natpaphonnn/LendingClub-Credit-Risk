"""Discrete-time competing-risks hazard (multinomial logit on loan-months) — prereg §A / §B.

outcome 0 = no event, 1 = default, 2 = prepay. Weighted Newton-Raphson (own implementation).
Design per loan-month: [1, B-spline(MOB) (5 cols; 6 df incl. intercept), lp, lp*t/36, int_rate_z, log_amt_z, (u, d12u)]
"""
import numpy as np
import pandas as pd
from scipy.interpolate import BSpline

DEG = 3
KNOTS = np.r_[[1.0] * (DEG + 1), 1 + 35 / 3, 1 + 70 / 3, [36.0] * (DEG + 1)]   # 2 interior knots -> 6 basis
_T = np.arange(1, 37, dtype=float)
_BASIS = BSpline.design_matrix(_T, KNOTS, DEG).toarray()[:, 1:]                  # drop 1st (intercept) -> 5 cols


def mob_basis(t):
    return _BASIS[np.asarray(t, int) - 1]


class Scaler:
    def __init__(self, loans):
        self.mu_r, self.sd_r = loans.int_rate.mean(), loans.int_rate.std()
        la = np.log(loans.loan_amnt)
        self.mu_a, self.sd_a = la.mean(), la.std()

    def loan_cols(self, loans):
        return np.column_stack([loans.lp.to_numpy(float),
                                ((loans.int_rate - self.mu_r) / self.sd_r).to_numpy(float),
                                ((np.log(loans.loan_amnt) - self.mu_a) / self.sd_a).to_numpy(float)])


def design(t, L, macro=None):
    """t: (n,) MOB; L: (n,3) loan cols [lp, rate_z, amt_z]; macro: (n,2) [u, d12u] or None."""
    t = np.asarray(t)
    cols = [np.ones((len(t), 1)), mob_basis(t), L[:, :1], (L[:, 0] * t / 36.0)[:, None], L[:, 1:3]]
    if macro is not None:
        cols.append(macro)
    return np.hstack(cols)


NAMES = ["const"] + [f"mob_b{i}" for i in range(1, 6)] + ["lp", "lp_x_t", "int_rate_z", "log_amt_z"]


def expand(loans, nonevent_frac=1.0, seed=0):
    """Loan-month panel: returns (loan_row_idx, t, y, w). Optional subsampling of non-event rows (weight 1/frac)."""
    T = loans["T"].to_numpy().astype(int)
    ev = loans["event"].to_numpy().astype(int)
    idx = np.repeat(np.arange(len(loans)), T)
    start = np.repeat(np.cumsum(T) - T, T)
    t = np.arange(len(idx)) - start + 1
    y = np.where(t == np.repeat(T, T), np.repeat(ev, T), 0).astype(np.int8)
    w = np.ones(len(idx))
    if nonevent_frac < 1.0:
        rng = np.random.default_rng(seed)
        keep = (y > 0) | (rng.random(len(idx)) < nonevent_frac)
        idx, t, y = idx[keep], t[keep], y[keep]
        w = np.where(y > 0, 1.0, 1.0 / nonevent_frac)
    return idx, t, y, w


def _probs(X, B):
    eta = X @ B                                   # (n, 2)
    m = np.maximum(eta.max(axis=1, keepdims=True), 0)
    e = np.exp(eta - m)
    den = np.exp(-m) + e.sum(axis=1, keepdims=True)
    return e / den                                # P1, P2


class NotIdentifiedError(ValueError):
    pass


def check_identified(X, w, max_cond=1e10):
    """Gate review R7-1 / R2-1: every design column needs weighted support and the information matrix must be well
    conditioned — otherwise coefficients (e.g. late-MOB spline terms beyond the observed horizon) are not identified."""
    support = (np.abs(X) * w[:, None]).sum(0)
    dead = np.where(support <= 1e-8 * support.max())[0]
    if len(dead):
        raise NotIdentifiedError(f"design columns without support in the fitting data: {dead.tolist()}")
    Xs = X / np.sqrt((X ** 2 * w[:, None]).sum(0) / w.sum())
    cond = np.linalg.cond((Xs * w[:, None]).T @ Xs / w.sum())
    if cond > max_cond:
        raise NotIdentifiedError(f"information matrix ill-conditioned (cond = {cond:.3g})")
    return cond


def fit_mnl(X, y, w, B0=None, iters=30, tol=1e-7, ridge=1e-8, check=True):
    n, p = X.shape
    if check and B0 is None:
        check_identified(X, w)
    B = np.zeros((p, 2)) if B0 is None else B0.copy()
    Y = np.column_stack([(y == 1), (y == 2)]).astype(float)
    for it in range(iters):
        P = _probs(X, B)
        R = (Y - P) * w[:, None]
        g = np.concatenate([X.T @ R[:, 0], X.T @ R[:, 1]])
        H11 = (X * (w * P[:, 0] * (1 - P[:, 0]))[:, None]).T @ X
        H22 = (X * (w * P[:, 1] * (1 - P[:, 1]))[:, None]).T @ X
        H12 = -(X * (w * P[:, 0] * P[:, 1])[:, None]).T @ X
        H = np.block([[H11, H12], [H12, H22]]) + ridge * np.eye(2 * p)
        step = np.linalg.solve(H, g)
        B += step.reshape(2, p).T
        if np.abs(step).max() < tol:
            break
    cov = np.linalg.inv(H)
    return B, cov, it + 1


def hazards(L, B, macro_path=None, horizon=36, chunk=200_000):
    """L: (n,3) loan cols; macro_path: (n, horizon, 2) or None. Returns h_d, h_p arrays (n, horizon)."""
    n = len(L)
    hd = np.empty((n, horizon), np.float32)
    hp = np.empty((n, horizon), np.float32)
    for s in range(0, n, chunk):
        Lc = L[s:s + chunk]
        m = len(Lc)
        t = np.tile(np.arange(1, horizon + 1), m)
        Lr = np.repeat(Lc, horizon, axis=0)
        mac = None if macro_path is None else macro_path[s:s + chunk].reshape(m * horizon, 2)
        P = _probs(design(t, Lr, mac), B)
        hd[s:s + chunk] = P[:, 0].reshape(m, horizon)
        hp[s:s + chunk] = P[:, 1].reshape(m, horizon)
    return hd, hp


def cif(hd, hp):
    """Returns S_prev (n,H) = survival to start of t, marginal default prob md (n,H), CIF_d (n,H)."""
    surv = np.cumprod(1 - hd - hp, axis=1)
    s_prev = np.hstack([np.ones((len(hd), 1), np.float32), surv[:, :-1]])
    md = s_prev * hd
    return s_prev, md, np.cumsum(md, axis=1)


def coef_table(B, cov, names):
    p = len(names)
    se = np.sqrt(np.diag(cov))
    rows = []
    for k, nm in ((0, "default"), (1, "prepay")):
        for j, v in enumerate(names):
            rows.append({"cause": nm, "term": v, "coef": B[j, k], "se": se[k * p + j]})
    return pd.DataFrame(rows)
