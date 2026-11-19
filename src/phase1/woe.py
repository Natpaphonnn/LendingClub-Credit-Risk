"""Monotonic WoE binning (pre-registered algorithm, notes/02_prereg_phase1.md §4).

WoE = ln(%good / %bad)  (higher WoE = safer).
Numeric: 20 quantile fine bins -> pool-adjacent-violators to make the bad rate monotone in the Spearman direction
-> merge bins < 5% of train into the adjacent bin with the closest bad rate -> missing gets its own bin if >= 0.5%,
else joins the non-missing bin with the closest bad rate.
Categorical: categories < 1% -> "OTHER"; unseen categories at scoring time -> "OTHER" (or WoE 0 if no OTHER bin).
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

EPS = 0.5  # additive smoothing on counts


@dataclass
class Binning:
    name: str
    kind: str                       # "num" | "cat"
    cuts: list = field(default_factory=list)          # numeric: right-closed upper bounds (last = +inf)
    cat_map: dict = field(default_factory=dict)       # categorical: raw value -> bin label
    labels: list = field(default_factory=list)        # bin labels in order (incl. "MISSING"/"OTHER")
    woe: dict = field(default_factory=dict)           # label -> WoE
    table: pd.DataFrame = None
    iv: float = 0.0
    missing_to: str = None          # label that missing values map to

    def assign(self, x: pd.Series) -> pd.Series:
        if self.kind == "num":
            v = x.to_numpy(dtype=float)
            idx = np.searchsorted(np.asarray(self.cuts, dtype=float), v, side="left")
            idx = np.minimum(idx, len(self.cuts) - 1)
            lab = np.asarray(self.labels_num, dtype=object)[idx]
            lab = np.where(np.isnan(v), self.missing_to, lab)
            return pd.Series(lab, index=x.index)
        s = x.astype("object").where(x.notna(), "MISSING")
        other = "OTHER" if "OTHER" in self.woe else None
        return s.map(lambda c: self.cat_map.get(c, other))

    def transform(self, x: pd.Series) -> pd.Series:
        return self.assign(x).map(self.woe).fillna(0.0).astype(float)

    @property
    def labels_num(self):
        return [lab for lab in self.labels if lab != "MISSING"]


def _woe_table(labels_in_order, lab, y):
    df = pd.DataFrame({"lab": lab, "y": y})
    g = df.groupby("lab", observed=True)["y"].agg(n="size", bad="sum").reindex(labels_in_order).fillna(0)
    g["good"] = g["n"] - g["bad"]
    tb, tg = g["bad"].sum(), g["good"].sum()
    g["pct_n"] = g["n"] / g["n"].sum()
    g["bad_rate"] = g["bad"] / g["n"].where(g["n"] > 0)
    g["woe"] = np.log(((g["good"] + EPS) / (tg + EPS)) / ((g["bad"] + EPS) / (tb + EPS)))
    g["iv_part"] = ((g["good"] + EPS) / (tg + EPS) - (g["bad"] + EPS) / (tb + EPS)) * g["woe"]
    return g


def _fmt(v):
    return f"{v:,.4g}"


def fit_numeric(name, x: pd.Series, y: pd.Series, min_share=0.05, missing_min=0.005, n_fine=20) -> Binning:
    x = x.astype(float)
    y = y.astype(float)
    nn = x.notna()
    xv, yv = x[nn].to_numpy(), y[nn].to_numpy()
    rho = spearmanr(xv, yv).statistic if len(np.unique(xv)) > 1 else 0.0
    increasing = bool(rho >= 0)            # bad rate increases with x
    qs = np.unique(np.quantile(xv, np.linspace(0, 1, n_fine + 1)[1:-1]))
    cuts = list(qs) + [np.inf]
    idx = np.searchsorted(np.asarray(cuts), xv, side="left")
    bins = [[cuts[i], float(yv[idx == i].sum()), float((idx == i).sum())] for i in range(len(cuts))]
    bins = [b for b in bins if b[2] > 0]

    # pool adjacent violators on bad rate
    def viol(a, b):
        ra, rb = a[1] / a[2], b[1] / b[2]
        return ra >= rb if increasing else ra <= rb

    stack = []
    for b in bins:
        stack.append(list(b))
        while len(stack) > 1 and viol(stack[-2], stack[-1]):
            top = stack.pop()
            stack[-1] = [top[0], stack[-1][1] + top[1], stack[-1][2] + top[2]]
    bins = stack
    # merge small bins into the adjacent bin with the closest bad rate
    total = len(xv)
    while len(bins) > 1:
        shares = [b[2] / total for b in bins]
        i = int(np.argmin(shares))
        if shares[i] >= min_share:
            break
        r = bins[i][1] / bins[i][2]
        cands = [j for j in (i - 1, i + 1) if 0 <= j < len(bins)]
        j = min(cands, key=lambda k: abs(bins[k][1] / bins[k][2] - r))
        lo, hi = min(i, j), max(i, j)
        bins[lo:hi + 1] = [[bins[hi][0], bins[lo][1] + bins[hi][1], bins[lo][2] + bins[hi][2]]]

    b = Binning(name, "num")
    b.cuts = [bb[0] for bb in bins]
    b.cuts[-1] = np.inf
    lows = [-np.inf] + b.cuts[:-1]
    labs = [f"({_fmt(lo)}, {_fmt(hi)}]" if np.isfinite(hi) else f"> {_fmt(lo)}" for lo, hi in zip(lows, b.cuts)]
    if len(labs) == 1:
        labs = ["all"]
    b.labels = labs
    miss_share = 1 - nn.mean()
    lab_nonmiss = pd.Series(np.asarray(labs, dtype=object)[np.minimum(
        np.searchsorted(np.asarray(b.cuts), x.to_numpy(), side="left"), len(labs) - 1)], index=x.index)
    if miss_share >= missing_min:
        b.labels = labs + ["MISSING"]
        b.missing_to = "MISSING"
    elif miss_share > 0:
        rm = y[~nn].mean()
        rates = [bb[1] / bb[2] for bb in bins]
        b.missing_to = labs[int(np.argmin([abs(r - rm) for r in rates]))]
    else:
        b.missing_to = labs[int(np.argmin([abs(bb[1] / bb[2] - y.mean()) for bb in bins]))]
    lab = lab_nonmiss.where(nn, b.missing_to)
    t = _woe_table(b.labels, lab, y)
    b.woe = t["woe"].to_dict()
    b.iv = float(t["iv_part"].sum())
    b.table = t.reset_index().rename(columns={"lab": "bin"})
    b.increasing = increasing
    return b


def fit_categorical(name, x: pd.Series, y: pd.Series, min_share=0.01) -> Binning:
    s = x.astype("object").where(x.notna(), "MISSING")
    share = s.value_counts(normalize=True)
    keep = set(share[share >= min_share].index)
    cat_map = {c: (c if c in keep else "OTHER") for c in share.index}
    lab = s.map(cat_map)
    labels = sorted(set(lab))
    t = _woe_table(labels, lab, y.astype(float))
    b = Binning(name, "cat", cat_map=cat_map, labels=labels)
    b.woe = t["woe"].to_dict()
    b.iv = float(t["iv_part"].sum())
    b.table = t.reset_index().rename(columns={"lab": "bin"})
    return b
