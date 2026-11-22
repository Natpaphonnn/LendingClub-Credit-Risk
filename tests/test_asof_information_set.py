"""Gate round 2 (R3-3): the as-of model (E2) uses no label before it was available on its decision date (31 Dec 2014)."""
import json
import sys
from pathlib import Path

import lightgbm as lgb
import pandas as pd
import pytest

from config import BASE, CHARGEOFF_LAG_M, FEATURES, INTERIM, split_mask, load_base
from riskutils import default_by_mob

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "phase4"))
from asof_info import DECISION, EVENT_LIMIT, TRAIN, VALID, event_month, label_available  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MODEL = INTERIM / "p4" / "asof_lgbm.txt"
need = pytest.mark.skipif(not BASE.exists() or not MODEL.exists(), reason="interim artefacts missing")


def test_label_availability_rule():
    issue = pd.Series(pd.to_datetime(["2013-06-01", "2013-07-01"]))
    av = label_available(issue, 6)
    assert av.iloc[0] == pd.Timestamp("2014-12-01") and av.iloc[1] == pd.Timestamp("2015-01-01")   # last usable vintage = 2013-06
    em = event_month(issue, pd.Series([12, None]))
    assert em.iloc[0] == pd.Timestamp("2014-06-01") and pd.isna(em.iloc[1])


@need
def test_every_fit_label_is_available_at_the_decision_date():
    df = load_base()
    fit = df[split_mask(df, TRAIN) | split_mask(df, VALID)]
    assert (label_available(fit.issue_dt, CHARGEOFF_LAG_M) <= pd.Timestamp(DECISION)).all()
    bad = fit[default_by_mob(fit.default_mob, 12) == 1]
    assert (event_month(bad.issue_dt, bad.default_mob) <= pd.Timestamp(EVENT_LIMIT)).all()
    # the fitted model saw exactly these rows and only application features
    meta = json.loads((ROOT / "reports" / "phase4" / "asof_model.json").read_text())
    assert meta["n_train"] == int(split_mask(df, TRAIN).sum()) and meta["n_valid"] == int(split_mask(df, VALID).sum())
    assert lgb.Booster(model_file=str(MODEL)).feature_name() == list(FEATURES)


@need
def test_no_oot_or_later_vintage_in_fit_windows():
    assert pd.Timestamp(VALID[1]) < pd.Timestamp("2015-01-01") and pd.Timestamp(TRAIN[1]) < pd.Timestamp(VALID[0])
