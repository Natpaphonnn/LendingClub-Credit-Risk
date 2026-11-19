"""M2 — LightGBM with pre-registered monotone constraints (prereg §4 M2). Grid of 12 configs, early stopping on
validation log loss; config chosen by validation log loss.

Outputs: data/interim/p1/lgbm.txt, data/interim/p1/scores_m2.parquet (row-level, git-ignored),
         reports/phase1/lgbm_grid.md, reports/phase1/lgbm_importance.md
Usage: nice -n 19 .venv/bin/python -I src/phase1/train_lgbm.py
"""
import itertools
import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (ART, CATEGORICAL, FEATURES, MONO_DEC, MONO_INC, REP, SEED, TRAIN, VALID,  # noqa: E402
                    load_base, split_mask)

df = load_base()
tr_m = split_mask(df, TRAIN) & df.bad.notna()
va_m = split_mask(df, VALID) & df.bad.notna()

# categories fixed from train; unseen -> NaN
cats = {c: sorted(df.loc[tr_m, c].dropna().unique()) for c in CATEGORICAL}
X = df[FEATURES].copy()
for c in CATEGORICAL:
    X[c] = pd.Categorical(X[c], categories=cats[c])
mono = [(-1 if f in MONO_DEC else 1 if f in MONO_INC else 0) for f in FEATURES]

dtr = lgb.Dataset(X[tr_m], df.loc[tr_m, "bad"], categorical_feature=CATEGORICAL, free_raw_data=False)
dva = lgb.Dataset(X[va_m], df.loc[va_m, "bad"], reference=dtr, categorical_feature=CATEGORICAL, free_raw_data=False)

rows, best = [], None
for nl, mcs, l2 in itertools.product([15, 31, 63], [200, 1000], [0, 10]):
    params = dict(objective="binary", metric="binary_logloss", learning_rate=0.05, num_leaves=nl,
                  min_child_samples=mcs, lambda_l2=l2, feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1,
                  monotone_constraints=mono, monotone_constraints_method="advanced", seed=SEED, num_threads=4,
                  verbose=-1, deterministic=True, force_row_wise=True)
    ev = {}
    m = lgb.train(params, dtr, num_boost_round=3000, valid_sets=[dva], valid_names=["valid"],
                  callbacks=[lgb.early_stopping(100, verbose=False), lgb.record_evaluation(ev)])
    ll = min(ev["valid"]["binary_logloss"])
    rows.append({"num_leaves": nl, "min_child_samples": mcs, "lambda_l2": l2, "best_iter": m.best_iteration,
                 "valid_logloss": round(ll, 5)})
    print(rows[-1])
    if best is None or ll < best[1]:
        best = (m, ll, params)

m, ll, params = best
m.save_model(str(ART / "lgbm.txt"), num_iteration=m.best_iteration)
(ART / "lgbm_cats.json").write_text(json.dumps(cats))
p = m.predict(X, num_iteration=m.best_iteration)
pd.DataFrame({"pd_m2": p.astype(np.float32)}, index=df.index).to_parquet(ART / "scores_m2.parquet")

grid = pd.DataFrame(rows)
imp = pd.DataFrame({"feature": FEATURES, "monotone": mono,
                    "gain": m.feature_importance("gain", iteration=m.best_iteration)})
imp["gain_pct"] = (100 * imp.gain / imp.gain.sum()).round(2)
imp = imp.sort_values("gain", ascending=False).drop(columns="gain")
sel = {k: params[k] for k in ("num_leaves", "min_child_samples", "lambda_l2")}
(REP / "lgbm_grid.md").write_text(
    f"# M2 LightGBM grid (selection by validation log loss)\n\nSelected: {sel}, best_iter={m.best_iteration}, "
    f"valid logloss={ll:.5f}\n\n" + grid.to_markdown(index=False) + "\n")
(REP / "lgbm_importance.md").write_text("# M2 gain importance (%)\n\n" + imp.to_markdown(index=False) + "\n")
print("selected", sel, m.best_iteration, ll)
