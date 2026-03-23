import pandas as pd
from sklearn.ensemble import RandomForestClassifier


def train_random_forest(X: pd.DataFrame, y: pd.Series) -> RandomForestClassifier:
    """Train a baseline RandomForest model for offer completion prediction."""
    model = RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1)
    model.fit(X, y)
    return model
