"""Shared LightGBM model frame and scoring (gate round 2, R10-12).

One place builds the model matrix for every stage: categories are fixed from the training window, values not seen in training are mapped
to missing *explicitly* (LightGBM routes them like a missing value; no reliance on pandas' deprecated silent coercion) and counted, so
unseen-category drift can be reported.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd


def fit_categories(df: pd.DataFrame, mask, categorical) -> dict:
    """Category levels per categorical column, from the rows in `mask` (the training window)."""
    return {c: sorted(df.loc[mask, c].dropna().unique()) for c in categorical}


def load_categories(path) -> dict:
    return json.loads(Path(path).read_text())


def model_frame(df: pd.DataFrame, features, categorical, cats: dict):
    """Returns (X, unseen): X = df[features] with categorical columns cast to the fixed levels; unseen = {column: count of
    non-missing values outside the training levels} (those become missing)."""
    X = df[list(features)].copy()
    unseen = {}
    for c in categorical:
        known = X[c].isin(cats[c])
        unseen[c] = int((X[c].notna() & ~known).sum())
        X[c] = pd.Categorical(X[c].where(known), categories=cats[c])
    return X, unseen


def score(booster, df: pd.DataFrame, features, categorical, cats: dict, num_iteration=None):
    """Predicted probability for every row of df, plus the unseen-category counts."""
    X, unseen = model_frame(df, features, categorical, cats)
    return np.asarray(booster.predict(X, num_iteration=num_iteration)), unseen
