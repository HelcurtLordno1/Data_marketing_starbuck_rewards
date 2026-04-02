import numpy as np
import pandas as pd
from scipy.sparse.linalg import svds


def build_user_offer_matrix(
    df: pd.DataFrame, user_col: str, offer_col: str, value_col: str
) -> pd.DataFrame:
    """Create a user-offer interaction matrix for collaborative filtering.

    Parameters
    ----------
    df        : DataFrame chứa dữ liệu interaction
    user_col  : tên cột user/person (ví dụ: 'person')
    offer_col : tên cột offer (ví dụ: 'offer_id')
    value_col : tên cột giá trị (ví dụ: 'offer_success')

    Returns
    -------
    pd.DataFrame — rows = users, columns = offers, values = aggregated score
    """
    return df.pivot_table(
        index=user_col, columns=offer_col, values=value_col, fill_value=0
    )


def fit_svd(
    user_offer_matrix: pd.DataFrame, k: int = 5
) -> pd.DataFrame:
    """Perform truncated SVD and return predicted rating matrix.

    Parameters
    ----------
    user_offer_matrix : pd.DataFrame
        Output của build_user_offer_matrix(). 
        Rows = users, Columns = offers, Values = 0/1
    k : int
        Số latent factors. Nên dùng 3-5 cho 10 offers.
        Sẽ tự giảm nếu k >= min(rows, cols).

    Returns
    -------
    pd.DataFrame — predicted ratings, clipped vào [0, 1]
    """
    k = min(k, min(user_offer_matrix.shape) - 1)
    U, sigma, Vt = svds(user_offer_matrix.values.astype(float), k=k)
    predicted = U @ np.diag(sigma) @ Vt
    return pd.DataFrame(
        predicted.clip(0, 1),
        index=user_offer_matrix.index,
        columns=user_offer_matrix.columns,
    )


def score_validation_set(
    svd_predictions: pd.DataFrame,
    valid_df: pd.DataFrame,
    user_col: str = "person",
    offer_col: str = "offer_id",
    fallback: float = 0.0,
) -> pd.Series:
    """Lookup SVD predicted scores for validation set rows.

    Với user hoặc offer không có trong train (cold-start),
    trả về giá trị fallback.

    Parameters
    ----------
    svd_predictions : pd.DataFrame — output của fit_svd()
    valid_df        : DataFrame validation, phải chứa user_col và offer_col
    fallback        : score mặc định cho cold-start users/offers

    Returns
    -------
    pd.Series — predicted scores, cùng index với valid_df
    """
    scores = []
    for _, row in valid_df.iterrows():
        user = row[user_col]
        offer = row[offer_col]
        if user in svd_predictions.index and offer in svd_predictions.columns:
            scores.append(svd_predictions.loc[user, offer])
        else:
            scores.append(fallback)
    return pd.Series(scores, index=valid_df.index)
