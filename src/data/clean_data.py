from pathlib import Path

import pandas as pd

from src.utils.io import read_json_lines, write_csv


def build_clean_dataset(portfolio_path: Path, profile_path: Path, transcript_path: Path) -> pd.DataFrame:
    """Load raw Starbucks files and return a merged dataframe.

    This is a starter scaffold; Week 1 team work should implement the full business logic.
    """
    portfolio_df = read_json_lines(portfolio_path)
    profile_df = read_json_lines(profile_path)
    transcript_df = read_json_lines(transcript_path)

    # Placeholder merge to provide a valid starting point for team implementation.
    merged = transcript_df.copy()
    merged["portfolio_records"] = len(portfolio_df)
    merged["profile_records"] = len(profile_df)
    return merged


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    data_dir = project_root / "data"
    processed_path = data_dir / "processed" / "cleaned_data.csv"

    df = build_clean_dataset(
        portfolio_path=data_dir / "portfolio.json",
        profile_path=data_dir / "profile.json",
        transcript_path=data_dir / "transcript.json",
    )
    write_csv(df, processed_path)
    print(f"Saved cleaned dataset to {processed_path}")


if __name__ == "__main__":
    main()
