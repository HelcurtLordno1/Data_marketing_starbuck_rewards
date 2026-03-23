import pandas as pd

from src.data.build_features import add_core_features


def test_add_core_features_returns_dataframe():
    df = pd.DataFrame({"age": [21, 38, 63]})
    out = add_core_features(df)
    assert isinstance(out, pd.DataFrame)
    assert "age_group" in out.columns
