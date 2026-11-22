"""Gate round 2 (R10-12): the shared model frame maps unseen categories to missing explicitly and counts them."""
import numpy as np
import pandas as pd

from scoring import fit_categories, model_frame


def test_unseen_categories_become_missing_and_are_counted():
    df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "c": ["a", "b", "z", None]})
    cats = fit_categories(df, np.array([True, True, False, False]), ["c"])
    assert cats == {"c": ["a", "b"]}
    X, unseen = model_frame(df, ["x", "c"], ["c"], cats)
    assert unseen == {"c": 1}
    assert list(X.c.cat.categories) == ["a", "b"]
    assert X.c.isna().tolist() == [False, False, True, True]
    assert X.x.tolist() == [1.0, 2.0, 3.0, 4.0]
