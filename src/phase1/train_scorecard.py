"""M1 — WoE/IV logistic scorecard (prereg §4 M1). Fit on train only; C chosen on validation log loss.

Outputs: data/interim/p1/scorecard.pkl, data/interim/p1/scores_m1.parquet (row-level, git-ignored)
         reports/phase1/iv_table.md, reports/phase1/scorecard_points.md, reports/phase1/scorecard_selection.md
Usage: nice -n 19 .venv/bin/python -I src/phase1/train_scorecard.py
"""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (ART, load_base, split_mask, BASE_ODDS, BASE_SCORE, CATEGORICAL, FEATURES, PDO, REP, TRAIN, VALID)  # noqa: E402
from woe import fit_categorical, fit_numeric  # noqa: E402

ART.mkdir(parents=True, exist_ok=True)
REP.mkdir(parents=True, exist_ok=True)
log = []


def say(s=""):
    print(s)
    log.append(s)


df = load_base()
tr = df[split_mask(df, TRAIN) & df.bad.notna()]
va = df[split_mask(df, VALID) & df.bad.notna()]
say(f"train n={len(tr):,} bad={tr.bad.mean():.4f} | valid n={len(va):,} bad={va.bad.mean():.4f}")

# ---- binning on train
bins = {}
for f in FEATURES:
    bins[f] = fit_categorical(f, tr[f], tr.bad) if f in CATEGORICAL else fit_numeric(f, tr[f], tr.bad)
iv = pd.DataFrame({"feature": list(bins), "iv": [bins[f].iv for f in bins], "n_bins": [len(bins[f].labels) for f in bins]})
iv = iv.sort_values("iv", ascending=False).reset_index(drop=True)

# ---- selection: IV >= 0.02 -> correlation filter |r| > 0.6 -> top 20
cand = iv[iv.iv >= 0.02].feature.tolist()
Wtr = pd.DataFrame({f: bins[f].transform(tr[f]) for f in cand})
corr = Wtr.corr().abs()
kept, dropped_corr = [], {}
for f in cand:  # already sorted by IV desc
    clash = [k for k in kept if corr.loc[f, k] > 0.6]
    if clash:
        dropped_corr[f] = f"|r|={corr.loc[f, clash[0]]:.2f} with {clash[0]}"
    else:
        kept.append(f)
sel = kept[:20]
iv["status"] = iv.feature.map(lambda f: "selected(pre-sign)" if f in sel else (
    "IV<0.02" if f not in cand else (f"corr drop: {dropped_corr[f]}" if f in dropped_corr else "beyond top 20")))

Wva = pd.DataFrame({f: bins[f].transform(va[f]) for f in sel})
Wtr = Wtr[sel]


def fit_best(cols):
    best = None
    for C in [0.01, 0.1, 1, 10]:
        m = LogisticRegression(C=C, max_iter=2000).fit(Wtr[cols].to_numpy(), tr.bad.to_numpy())
        ll = log_loss(va.bad, m.predict_proba(Wva[cols].to_numpy())[:, 1])
        say(f"  C={C:<5} features={len(cols)} valid logloss={ll:.5f}")
        if best is None or ll < best[1]:
            best = (m, ll, C)
    return best


cols = list(sel)
ivmap = dict(zip(iv.feature, iv.iv))
sign_drops = []
while True:
    m, ll, C = fit_best(cols)
    coef = dict(zip(cols, m.coef_[0]))
    wrong = [c for c in cols if coef[c] >= 0]
    if not wrong:
        break
    drop = min(wrong, key=lambda c: ivmap[c])
    sign_drops.append(drop)
    say(f"  wrong sign (beta>=0) for {wrong}; drop {drop} (lowest IV) and refit")
    cols.remove(drop)
iv.loc[iv.feature.isin(sign_drops), "status"] = "dropped: wrong sign"
iv.loc[iv.feature.isin(cols), "status"] = "FINAL"
say(f"final: C={C}, {len(cols)} characteristics, valid logloss={ll:.5f}")

# ---- points scaling
factor = PDO / np.log(2)
offset = BASE_SCORE - factor * np.log(BASE_ODDS)
alpha = m.intercept_[0]
n = len(cols)
rows = []
for c in cols:
    b = bins[c]
    for lab in b.labels:
        w = b.woe[lab]
        pts = int(round(-(coef[c] * w + alpha / n) * factor + offset / n))
        t = b.table.set_index("bin").loc[lab]
        rows.append({"characteristic": c, "bin": lab, "pct_train": round(100 * t.pct_n, 1),
                     "bad_rate_train": round(100 * t.bad_rate, 1) if pd.notna(t.bad_rate) else None,
                     "woe": round(w, 3), "points": pts})
pts = pd.DataFrame(rows)
points = {c: dict(zip(pts[pts.characteristic == c].bin, pts[pts.characteristic == c].points)) for c in cols}

sc = {"bins": {c: bins[c] for c in cols}, "all_bins": bins, "cols": cols, "coef": coef, "alpha": alpha, "C": C,
      "points": points, "factor": factor, "offset": offset}
with open(ART / "scorecard.pkl", "wb") as fh:
    pickle.dump(sc, fh)


def score_frame(d):
    P = pd.DataFrame(index=d.index)
    L = pd.DataFrame(index=d.index)
    for c in cols:
        lab = bins[c].assign(d[c])
        L[c] = lab
        pts = lab.map(points[c])
        assert pts.notna().all(), f"{c}: unmapped bin (gate R4-5: no silent 0 points)"
        P[c] = pts.astype(np.int16)
    s = P.sum(axis=1).astype(np.int32)
    pd_ = 1 / (1 + np.exp((s - offset) / factor))
    return s, pd_, P, L


s, p, P, L = score_frame(df)
out = pd.DataFrame({"score_m1": s, "pd_m1": p.astype(np.float32)})
out = pd.concat([out, P.add_prefix("pts__"), L.add_prefix("bin__")], axis=1)
out.to_parquet(ART / "scores_m1.parquet")

# ---- reports
coef_tab = pd.DataFrame({"characteristic": cols, "beta": [round(coef[c], 4) for c in cols],
                         "iv_train": [round(ivmap[c], 4) for c in cols],
                         "min_pts": [min(points[c].values()) for c in cols], "max_pts": [max(points[c].values()) for c in cols]})
(REP / "iv_table.md").write_text("# IV on train (2012-09..2013-12) and selection status\n\n"
                                 + iv.round(4).to_markdown(index=False) + "\n")
(REP / "scorecard_points.md").write_text(
    f"# M1 scorecard — points table\n\nPDO={PDO}, {BASE_SCORE} points at good:bad odds {BASE_ODDS}:1; "
    f"factor={factor:.3f}, offset={offset:.2f}; intercept alpha={alpha:.4f}; L2 C={C}. Higher score = lower risk.\n\n"
    "## Characteristics\n\n" + coef_tab.to_markdown(index=False) + "\n\n## Attributes\n\n" + pts.to_markdown(index=False) + "\n")
(REP / "scorecard_selection.md").write_text("# M1 selection log\n\n```\n" + "\n".join(log) + "\n```\n")
print(coef_tab.to_string())
print("score range (all rows):", int(s.min()), int(s.max()))
