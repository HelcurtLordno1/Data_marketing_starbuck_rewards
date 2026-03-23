import pandas as pd


def add_core_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add baseline feature columns used by Week 2 models."""
    out = df.copy()
    if "age" in out.columns:
        out["age_group"] = pd.cut(
            out["age"],
            bins=[0, 24, 34, 44, 54, 64, 120],
            labels=["18-24", "25-34", "35-44", "45-54", "55-64", "65+"],
            include_lowest=True,
        )
    return out
