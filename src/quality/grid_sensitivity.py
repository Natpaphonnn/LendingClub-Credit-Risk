"""DESCRIPTIVE robustness (independent review MA-2): retrain all 12 pre-registered LightGBM configs and report validation log loss
alongside OOT metrics. Does NOT change the champion (selection stays by validation log loss, as pre-registered).
Output: reports/quality/grid_sensitivity.md
"""
import itertools
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "phase1"))
from config import CATEGORICAL, FEATURES, MONO_DEC, MONO_INC, OOT, SEED, TRAIN, VALID, load_base, split_mask  # noqa: E402
from metrics import Disc  # noqa: E402

df = load_base()
tr, va, oo = (split_mask(df, w) & df.bad.notna() for w in (TRAIN, VALID, OOT))
cats = {c: sorted(df.loc[tr, c].dropna().unique()) for c in CATEGORICAL}
X = df[FEATURES].copy()
for c in CATEGORICAL:
    X[c] = pd.Categorical(X[c], categories=cats[c])
mono = [(-1 if f in MONO_DEC else 1 if f in MONO_INC else 0) for f in FEATURES]
dtr = lgb.Dataset(X[tr], df.loc[tr, "bad"], categorical_feature=CATEGORICAL, free_raw_data=False)
dva = lgb.Dataset(X[va], df.loc[va, "bad"], reference=dtr, categorical_feature=CATEGORICAL, free_raw_data=False)
y = df.loc[oo, "bad"].to_numpy()
rows = []
for nl, mcs, l2 in itertools.product([15, 31, 63], [200, 1000], [0, 10]):
    params = dict(objective="binary", metric="binary_logloss", learning_rate=0.05, num_leaves=nl, min_child_samples=mcs,
                  lambda_l2=l2, feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, monotone_constraints=mono,
                  monotone_constraints_method="intermediate", seed=SEED, num_threads=4, verbose=-1, deterministic=True,
                  force_row_wise=True)
    ev = {}
    m = lgb.train(params, dtr, 3000, valid_sets=[dva], valid_names=["v"],
                  callbacks=[lgb.early_stopping(100, verbose=False), lgb.record_evaluation(ev)])
    p = m.predict(X[oo], num_iteration=m.best_iteration)
    rows.append({"num_leaves": nl, "min_child_samples": mcs, "lambda_l2": l2, "best_iter": m.best_iteration,
                 "valid_logloss": min(ev["v"]["binary_logloss"]), "OOT Gini": 100 * (2 * roc_auc_score(y, p) - 1),
                 "OOT KS": 100 * Disc(p, y).auc_ks()[1], "OOT CITL pp": 100 * (p.mean() - y.mean())})
    print(rows[-1], flush=True)
T = pd.DataFrame(rows).sort_values("valid_logloss").reset_index(drop=True)
T["selected"] = ["◀ champion"] + [""] * (len(T) - 1)
rng = {k: (T[k].min(), T[k].max()) for k in ("valid_logloss", "OOT Gini", "OOT KS", "OOT CITL pp")}
import json  # noqa: E402
g1 = 100 * json.loads((ROOT / "reports" / "phase1" / "metrics.json").read_text())["oot_2015"]["M1_scorecard"]["gini"]
margin = rng["OOT Gini"][0] - g1
md = ("# LightGBM grid — sensitivity of OOT metrics (DESCRIPTIVE; champion unchanged)\n\n"
      f"Validation log loss spread across the 12 pre-registered configs: {rng['valid_logloss'][1]-rng['valid_logloss'][0]:.5f} "
      f"— selection among them is close to noise. OOT Gini range {rng['OOT Gini'][0]:.2f}–{rng['OOT Gini'][1]:.2f}, "
      f"KS {rng['OOT KS'][0]:.2f}–{rng['OOT KS'][1]:.2f}, CITL {rng['OOT CITL pp'][0]:.2f} to {rng['OOT CITL pp'][1]:.2f} pp. "
      f"Weakest config minus scorecard OOT Gini ({g1:.2f}) = {margin:.2f} → the '≥ 2.0 Gini' conclusion "
      f"{'holds for every config' if margin >= 2.0 else 'does NOT hold for every config'}; every config under-predicts PD on OOT.\n\n" + T.round(4).to_markdown(index=False) + "\n")
(ROOT / "reports" / "quality" / "grid_sensitivity.md").write_text(md)
print(md)
