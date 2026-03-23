import pandas as pd


def recommend_best_offer(scored_offers: pd.DataFrame, customer_id: str) -> pd.Series:
    """Return the highest-probability offer row for one customer.

    Expected columns: customer_id, offer_id, probability, expected_revenue.
    """
    customer_scores = scored_offers[scored_offers["customer_id"] == customer_id]
    if customer_scores.empty:
        raise ValueError(f"No scores found for customer_id={customer_id}")
    return customer_scores.sort_values("probability", ascending=False).iloc[0]
