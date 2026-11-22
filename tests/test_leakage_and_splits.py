"""Leakage and split integrity — proven from feature lists, trained model objects and source code.
Data-dependent tests skip if the (git-ignored) interim artefacts are missing."""
import json
import pickle
import re
from pathlib import Path

import pandas as pd
import pytest

from config import ART, BASE, CATEGORICAL, DERIVED, FEATURES, NUMERIC, OOT, TRAIN, VALID, split_mask
from leakage_map import classify

ROOT = Path(__file__).resolve().parents[1]
LK = classify()
DERIVED_SOURCES = {"fico": ["fico_range_low"], "credit_hist_months": ["earliest_cr_line"],
                   "loan_to_income": ["loan_amnt", "annual_inc"], "emp_length_yrs": ["emp_length"]}
need_data = pytest.mark.skipif(not BASE.exists() or not (ART / "lgbm.txt").exists(), reason="interim artefacts missing")


# ---------------------------------------------------------------- leakage (static)
def test_every_raw_feature_is_application_time():
    for f in NUMERIC + CATEGORICAL:
        assert LK[f][0] == "APP", f"{f} is {LK[f][0]}"


def test_derived_features_use_only_application_columns():
    assert set(DERIVED) == set(DERIVED_SOURCES)
    for d, srcs in DERIVED_SOURCES.items():
        for s in srcs:
            assert LK[s][0] == "APP", (d, s)


def test_no_lc_post_id_target_names_in_features():
    banned = {c for c, (k, _) in LK.items() if k in {"LC", "POST", "ID", "TARGET"}}
    assert not banned & set(FEATURES)
    assert not {"addr_state", "zip_code", "desc", "emp_title", "title"} & set(FEATURES)   # design exclusions


def test_derived_sql_reads_only_declared_sources():
    sql = (ROOT / "src/phase1/build_dataset.py").read_text()
    assert re.search(r"TRY_CAST\(fico_range_low AS DOUBLE\) \+ 2\)::FLOAT AS fico", sql)
    assert "earliest_cr_line, '%b-%Y')::DATE, issue_dt)::FLOAT AS credit_hist_months" in sql
    assert re.search(r"TRY_CAST\(loan_amnt AS DOUBLE\) / NULLIF\(TRY_CAST\(annual_inc AS DOUBLE\), 0\)\)::FLOAT AS loan_to_income", sql)
    assert "END::FLOAT AS emp_length_yrs" in sql and "emp_length" in sql


def test_training_code_uses_feature_list_only():
    lgb_src = (ROOT / "src/phase1/train_lgbm.py").read_text()
    assert "X, unseen = model_frame(df, FEATURES, CATEGORICAL, cats)" in lgb_src        # shared helper (src/lib/scoring.py)
    helper = (ROOT / "src/lib/scoring.py").read_text()
    assert "X = df[list(features)].copy()" in helper                                     # the helper selects only the given features
    sc_src = (ROOT / "src/phase1/train_scorecard.py").read_text()
    assert "for f in FEATURES:" in sc_src


# ---------------------------------------------------------------- leakage (trained objects)
@need_data
def test_lgbm_model_features_equal_feature_list():
    import lightgbm as lgb
    booster = lgb.Booster(model_file=str(ART / "lgbm.txt"))
    assert booster.feature_name() == FEATURES


@need_data
def test_scorecard_characteristics_subset_of_features():
    with open(ART / "scorecard.pkl", "rb") as fh:
        sc = pickle.load(fh)
    assert set(sc["cols"]) <= set(FEATURES)
    assert set(sc["all_bins"]) == set(FEATURES)


def test_lifetime_model_covariates_documented():
    """Lifetime/ECL hazard uses the frozen application PD plus contract terms (int_rate is an LC pricing output, allowed
    only because the hazard model is not an application decision model — see notes/03_prereg_phase2.md §A)."""
    src = (ROOT / "src/phase2/hazard.py").read_text()
    assert re.search(r"loans\.lp.*\n.*int_rate.*\n.*loan_amnt", src)


# ---------------------------------------------------------------- splits
@need_data
def test_phase1_splits_disjoint_and_ordered():
    b = pd.read_parquet(BASE, columns=["id", "issue_dt"])
    b["issue_dt"] = pd.to_datetime(b.issue_dt)
    assert b.id.is_unique
    tr, va, oo = (b[split_mask(b, w)] for w in (TRAIN, VALID, OOT))
    assert not (set(tr.id) & set(va.id)) and not (set(tr.id) & set(oo.id)) and not (set(va.id) & set(oo.id))
    assert tr.issue_dt.max() < va.issue_dt.min() and va.issue_dt.max() < oo.issue_dt.min()


@need_data
def test_phase2_windows_and_population_consistency():
    p2 = pd.read_parquet(ROOT / "data/interim/p2_loans.parquet", columns=["id", "issue_dt", "yr"])
    p2["issue_dt"] = pd.to_datetime(p2.issue_dt)
    assert p2.id.is_unique
    b_fit = p2[(p2.issue_dt >= "2009-01-01") & (p2.issue_dt <= "2014-12-01")]
    oot = p2[p2.yr == 2015]
    assert b_fit.issue_dt.max() < oot.issue_dt.min()
    b = pd.read_parquet(BASE, columns=["id", "issue_dt"])
    b["issue_dt"] = pd.to_datetime(b.issue_dt)
    # same OOT population in Phase 1 and Phase 2
    assert set(b[split_mask(b, OOT)].id) == set(oot.id)


@need_data
def test_scores_aligned_to_base():
    n = len(pd.read_parquet(BASE, columns=["issue_dt"]))
    assert len(pd.read_parquet(ART / "scores_m1.parquet", columns=["score_m1"])) == n
    assert len(pd.read_parquet(ART / "scores_m2.parquet")) == n


@need_data
def test_oot_never_used_for_selection():
    """OOT appears only in evaluation/monitoring scripts, never in training/selection scripts."""
    for f in ("train_scorecard.py", "train_lgbm.py"):
        src = (ROOT / "src/phase1" / f).read_text()
        assert "OOT" not in src, f
    meta = json.loads((ROOT / "reports/phase1/metrics.json").read_text())
    assert "oot_2015" in meta and meta["champion"] in {"M1_scorecard", "M2_lgbm"}
