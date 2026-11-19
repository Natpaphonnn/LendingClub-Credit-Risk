"""Gate round 2 (R4-3): scorecard scaling, score→PD inversion, points sum and reason-code baseline on the trained artefact."""
import pickle

import numpy as np
import pandas as pd
import pytest

from config import ART

need = pytest.mark.skipif(not (ART / "scorecard.pkl").exists(), reason="interim artefacts missing")


@need
def test_pdo_scaling_and_pd_inversion():
    sc = pickle.load(open(ART / "scorecard.pkl", "rb"))
    assert sc["factor"] == pytest.approx(20 / np.log(2))
    assert sc["offset"] == pytest.approx(600 - sc["factor"] * np.log(50))
    pd_at = lambda s: 1 / (1 + np.exp((s - sc["offset"]) / sc["factor"]))  # noqa: E731
    assert pd_at(600) == pytest.approx(1 / 51)                              # odds 50:1 at 600
    odds = lambda s: (1 - pd_at(s)) / pd_at(s)                              # noqa: E731
    assert odds(620) / odds(600) == pytest.approx(2.0)                      # PDO 20 doubles the odds
    s = pd.read_parquet(ART / "scores_m1.parquet").sample(20_000, random_state=0)
    pts = s[[c for c in s.columns if c.startswith("pts__")]].sum(axis=1)
    assert (pts == s.score_m1).all()
    assert np.allclose(s.pd_m1, pd_at(s.score_m1), atol=1e-6)


@need
def test_points_monotone_in_woe_and_reason_baseline_is_max():
    sc = pickle.load(open(ART / "scorecard.pkl", "rb"))
    for c in sc["cols"]:
        w, p = sc["bins"][c].woe, sc["points"][c]
        labs = [k for k in w if k in p]
        order = np.argsort([w[k] for k in labs])
        pts = np.array([p[labs[i]] for i in order])
        assert (np.diff(pts) >= 0).all(), c                                  # higher WoE (safer) never gets fewer points
        best = labs[order[-1]]
        assert p[best] == max(p.values()), c                                 # reason-code baseline = max-points attribute
