import pandas as pd

from src.models.recommend import recommend_best_offer


def test_recommend_best_offer_returns_top_probability_row():
    scored = pd.DataFrame(
        {
            "customer_id": ["u1", "u1", "u2"],
            "offer_id": ["o1", "o2", "o3"],
            "probability": [0.2, 0.8, 0.5],
            "expected_revenue": [1.0, 3.0, 2.0],
        }
    )
    top = recommend_best_offer(scored, "u1")
    assert top["offer_id"] == "o2"
