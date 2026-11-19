"""Gate R5-1: the pre-registered monotone constraints must hold in the trained models (the first build used
monotone_constraints_method="advanced", which violated them for 22 of 34 constrained features).
Sweep each constrained feature over its observed quantiles on real rows; prediction must move in the stated direction."""
import json

import lightgbm as lgb
import numpy as np
import pandas as pd
import pytest

from config import ART, BASE, CATEGORICAL, FEATURES, MONO_DEC, MONO_INC, INTERIM, load_base

MODELS = [ART / "lgbm.txt", INTERIM / "p4" / "asof_lgbm.txt"]
CATS = [ART / "lgbm_cats.json", INTERIM / "p4" / "asof_cats.json"]


def test_intermediate_method_enforces_monotonicity_on_synthetic_data():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(20_000, 3))
    y = (rng.random(20_000) < 1 / (1 + np.exp(-(np.sin(3 * X[:, 0]) + X[:, 1])))).astype(float)
    m = lgb.train(dict(objective="binary", monotone_constraints=[1, -1, 0], monotone_constraints_method="intermediate",
                       num_leaves=31, verbose=-1, seed=0), lgb.Dataset(X, y), 200)
    base = X[:200].copy()
    grid = np.linspace(-3, 3, 41)
    for j, sgn in ((0, 1), (1, -1)):
        P = np.array([m.predict(np.where(np.arange(3) == j, g, base)) for g in grid])
        assert (sgn * np.diff(P, axis=0) >= -1e-12).all()


@pytest.mark.parametrize("k", [0, 1])
@pytest.mark.skipif(not BASE.exists(), reason="interim artefacts missing")
def test_trained_models_are_monotone(k):
    if not MODELS[k].exists():
        pytest.skip("model missing")
    b = lgb.Booster(model_file=str(MODELS[k]))
    cats = json.loads(CATS[k].read_text())
    df = load_base().sample(300, random_state=0)
    X = df[FEATURES].copy()
    for c in CATEGORICAL:
        X[c] = pd.Categorical(X[c], categories=cats[c])
    bad = []
    full = load_base()
    for f in MONO_DEC + MONO_INC:
        sgn = -1 if f in MONO_DEC else 1
        grid = np.unique(np.nanquantile(full[f].astype(float), np.linspace(0, 1, 25)))
        P = []
        for g in grid:
            Xg = X.copy()
            Xg[f] = g
            P.append(b.predict(Xg))
        if (sgn * np.diff(np.array(P), axis=0) < -1e-12).any():
            bad.append(f)
    assert bad == [], f"monotone constraint violated for {bad}"
