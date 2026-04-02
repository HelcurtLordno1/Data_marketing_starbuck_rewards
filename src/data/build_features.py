import numpy as np
import pandas as pd


def add_core_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add baseline feature columns used by Week 2 models.

    Features tạo ra:
    - age_group       : 6 bins theo demographic chuẩn
    - income_group    : 5 bins theo income quintiles
    - channel flags   : has_web_channel, has_email_channel, ...
    - membership_duration_months : tenure tính bằng tháng
    """
    out = df.copy()

    # 1) Age group
    if "age" in out.columns:
        out["age_group"] = pd.cut(
            out["age"],
            bins=[0, 25, 35, 45, 55, 65, np.inf],
            labels=["18-25", "26-35", "36-45", "46-55", "56-65", "66+"],
            include_lowest=True,
        ).astype(str)

    # 2) Income group
    if "income" in out.columns:
        out["income_group"] = pd.cut(
            out["income"],
            bins=[0, 40_000, 60_000, 80_000, 100_000, np.inf],
            labels=["low", "lower_middle", "middle", "upper_middle", "high"],
            include_lowest=True,
        ).astype(str)

    # 3) Channel availability flags
    for ch in ["web", "email", "mobile", "social"]:
        src_col = ch if ch in out.columns else f"channel_{ch}"
        if src_col in out.columns:
            out[f"has_{ch}_channel"] = (out[src_col] > 0).astype(int)

    # 4) Membership duration in months
    if "days_since_registration" in out.columns:
        out["membership_duration_months"] = (
            out["days_since_registration"] / 30.44
        ).round(2)

    return out
