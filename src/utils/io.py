from pathlib import Path

import pandas as pd


def ensure_parent_dir(path: Path) -> None:
    """Create parent directory if it does not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)


def read_json_lines(path: Path) -> pd.DataFrame:
    """Read line-delimited JSON into a pandas DataFrame."""
    return pd.read_json(path, orient="records", lines=True)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    """Write DataFrame to CSV with stable settings for reproducibility."""
    ensure_parent_dir(path)
    df.to_csv(path, index=False)
