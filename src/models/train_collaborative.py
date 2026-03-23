import pandas as pd


def build_user_offer_matrix(df: pd.DataFrame, user_col: str, offer_col: str, value_col: str) -> pd.DataFrame:
    """Create a user-offer interaction matrix for collaborative filtering."""
    return df.pivot_table(index=user_col, columns=offer_col, values=value_col, fill_value=0)
