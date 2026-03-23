from typing import Dict

from sklearn.metrics import accuracy_score, f1_score, mean_squared_error, precision_score, recall_score


def classification_metrics(y_true, y_pred) -> Dict[str, float]:
    """Return core classification metrics for weekly model comparison."""
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
    }


def mse_metric(y_true, y_pred) -> float:
    """Return mean squared error for tasks requiring regression-style checks."""
    return mean_squared_error(y_true, y_pred)
