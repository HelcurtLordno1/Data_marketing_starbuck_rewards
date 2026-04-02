from typing import Dict

from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    mean_squared_error,
    precision_score,
    recall_score,
    roc_auc_score,
    average_precision_score,
)


def classification_metrics(y_true, y_pred) -> Dict[str, float]:
    """Return core classification metrics for weekly model comparison."""
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
    }


def ranking_metrics(y_true, y_proba) -> Dict[str, float]:
    """Return ranking/probability metrics (cần predict_proba, không phải predict).

    Parameters
    ----------
    y_true  : array-like — nhãn thực (0/1)
    y_proba : array-like — xác suất predicted (0.0 - 1.0)
    """
    return {
        "roc_auc": roc_auc_score(y_true, y_proba),
        "pr_auc": average_precision_score(y_true, y_proba),
        "mse": mean_squared_error(y_true, y_proba),
    }


def full_evaluation(y_true, y_pred, y_proba) -> Dict[str, float]:
    """All-in-one: classification + ranking + MSE.

    Ví dụ sử dụng:
        metrics = full_evaluation(y_valid, model.predict(X), model.predict_proba(X)[:, 1])
    """
    result = classification_metrics(y_true, y_pred)
    result.update(ranking_metrics(y_true, y_proba))
    return result


def mse_metric(y_true, y_pred) -> float:
    """Return mean squared error for tasks requiring regression-style checks."""
    return mean_squared_error(y_true, y_pred)
