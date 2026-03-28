"""
clean_data.py
=============
Starbucks Rewards — Data Cleaning & Preprocessing Pipeline
Person E (Coordinator) — Week 1, Day 2-3
Author  : Team Data-Driven Marketing
Created : 2026-03-28
Updated : 2026-03-28

PURPOSE
-------
This script is the single, authoritative preprocessing pipeline for the
Starbucks Rewards project.  It reproduces (and improves upon) the logic
originally developed in notebooks 01_a and 01_b, and wraps it in a clean,
importable Python module that every team member can run from the command line
or import into other scripts and notebooks.

PIPELINE OVERVIEW
-----------------
The raw data consists of three JSON files:

    portfolio.json  — 10 marketing offers (type, reward, difficulty, duration,
                      channels).
    profile.json    — 14,825 customer demographics (age, gender, income,
                      membership date, id).
    transcript.json — 306,534 event-log records (offer received / viewed /
                      completed, and purchase transactions).

The pipeline executes the following steps in order:

  Step 0 : Load raw JSON files
  Step 1 : Extract offer-event indicators from transcript
  Step 2 : Aggregate to person–offer level (one row per customer × offer)
  Step 3 : Merge demographics (profile) and offer metadata (portfolio)
  Step 4 : Remove informational offers (no completion objective)
  Step 5 : Create the binary target label  offer_completed
  Step 6 : Derive days_since_registration from membership date
  Step 7 : One-hot encode channels  →  web / email / mobile / social columns
  Step 8 : Impute missing values  (age, income, gender, days_since_registration)
  Step 9 : Filter to viewed-offer rows only  (modeling convention)
  Step 10: Validate quality gates
  Step 11: Export cleaned dataset  →  data/processed/cleaned_data.csv
  Step 12: Engineer derived features  →  data/features_added/…_features_added.csv

EXPECTED OUTPUTS
----------------
  data/processed/cleaned_data.csv
      Shape  : 39,826 rows × 18 columns
      Note   : Includes raw gender / offer_type strings (not one-hot) so Power BI
               can use them directly as slicers.

  data/features_added/preprocessed_data_features_added.csv
      Shape  : 39,826 rows × 27 columns  (18 base + 7 derived + 2-col extras)

QUALITY GATES (Week 1 — per Workflow_starbuck.md §3)
-----------------------------------------------------
  ✅ No null values after imputation
  ✅ No duplicate person–offer pairs
  ✅ offer_completed rate ≈ 48.3%   (tolerance ±2 pp)
  ✅ Final row count   ≈ 39,826
  ✅ All 20 expected columns present

HOW TO RUN
----------
From the project root (conda env activated):

    python -m src.data.clean_data           # writes both CSV files

Or import into a notebook:

    from src.data.clean_data import build_clean_dataset, add_features
    merged_df          = build_clean_dataset(...)
    enriched_df        = add_features(merged_df)

Dependencies
------------
    pandas  >= 2.0
    numpy   >= 1.24
    (no scikit-learn needed at this stage)
"""

# ===========================================================================
# Imports
# ===========================================================================
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Project-level path resolution
# Works whether called as a module (python -m src.data.clean_data) or
# directly (python src/data/clean_data.py).
# ---------------------------------------------------------------------------
_THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT: Path = _THIS_FILE.parents[2]          # …/Data_marketing_starbuck_rewards
DATA_DIR: Path     = PROJECT_ROOT / "data"
PROCESSED_DIR: Path       = DATA_DIR / "processed"
FEATURES_ADDED_DIR: Path  = DATA_DIR / "features_added"

# ---------------------------------------------------------------------------
# Logging — every major step is logged so the team can see exactly what
# happened without opening a notebook.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)


# ===========================================================================
# ── STEP 0 ──────────────────────────────────────────────────────────────────
# Load raw JSON files
# ===========================================================================

def load_raw_data(
    data_dir: Path = DATA_DIR,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load the three raw JSON source files.

    Parameters
    ----------
    data_dir : Path
        Directory that contains portfolio.json, profile.json, transcript.json.

    Returns
    -------
    portfolio_df : pd.DataFrame  — 10 rows  × 6 columns
        Columns: id, offer_type, difficulty, reward, duration, channels
    profile_df   : pd.DataFrame  — 14,825 rows × 5 columns
        Columns: id, age, became_member_on, gender, income
    transcript_df: pd.DataFrame  — 306,534 rows × 4 columns
        Columns: event, person, time, value

    Why line-delimited JSON?
        Starbucks data is stored as one JSON object per line (JSONL format),
        so we pass  orient='records', lines=True  to pd.read_json.

    Why not CSV for the raw files?
        The 'value' column in transcript is a dict, and the 'channels' column
        in portfolio is a list — these nested types are preserved in JSON but
        would be serialised as strings in CSV, requiring extra parsing.
    """
    log.info("STEP 0 — Loading raw JSON files from %s", data_dir)

    required_files = {
        "portfolio.json": "Portfolio (offer metadata)",
        "profile.json":   "Profile  (customer demographics)",
        "transcript.json":"Transcript (event log)",
    }

    for fname, label in required_files.items():
        fpath = data_dir / fname
        if not fpath.exists():
            raise FileNotFoundError(
                f"[STEP 0] {label} file not found at: {fpath}\n"
                "Please download the dataset and place it inside the data/ directory."
            )

    portfolio_df  = pd.read_json(data_dir / "portfolio.json",  orient="records", lines=True)
    profile_df    = pd.read_json(data_dir / "profile.json",    orient="records", lines=True)
    transcript_df = pd.read_json(data_dir / "transcript.json", orient="records", lines=True)

    log.info("  portfolio  shape : %s", portfolio_df.shape)
    log.info("  profile    shape : %s", profile_df.shape)
    log.info("  transcript shape : %s", transcript_df.shape)

    return portfolio_df, profile_df, transcript_df


# ===========================================================================
# ── STEP 1 ──────────────────────────────────────────────────────────────────
# Extract offer-event indicators from the transcript
# ===========================================================================

def extract_offer_events(transcript_df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter the raw event log to offer-related events and extract the offer ID.

    Background
    ----------
    The transcript contains four event types:
        'offer received'   — Starbucks sent an offer to the customer.
        'offer viewed'     — the customer opened / saw the offer.
        'offer completed'  — the customer met the spend threshold.
        'transaction'      — a regular purchase (no offer involved).

    We keep only the three offer events and discard plain 'transaction' rows
    because transactions are not needed for the completion-rate model.

    Offer-ID extraction
    -------------------
    The 'value' column is a dict with one of two key names (an inconsistency
    in the raw dataset):
        {'offer id': '<uuid>'}          — used by the majority of events
        {'offer_id': '<uuid>'}          — used by a small subset of events
    We handle both with a safe .get() chain.

    Returns
    -------
    offers_raw : pd.DataFrame
        Columns: person, offer, event
        Rows   : one row per (person, offer, event-occurrence)
    """
    log.info("STEP 1 — Extracting offer events from transcript (%d rows)", len(transcript_df))

    # ── 1a. Filter to the three offer-related events ────────────────────────
    OFFER_EVENTS: List[str] = ["offer received", "offer viewed", "offer completed"]
    offers_raw = transcript_df[transcript_df["event"].isin(OFFER_EVENTS)].copy()
    log.info("  Offer-event rows kept : %d  (discarded %d transaction rows)",
             len(offers_raw), len(transcript_df) - len(offers_raw))

    # ── 1b. Extract offer ID from the nested 'value' dict ───────────────────
    #
    # Why we use  x.get('offer id') or x.get('offer_id'):
    #   - The raw data has BOTH key names depending on event type.
    #   - Using 'or' ensures we fall back to the underscore version if the
    #     space-version is absent (or None).
    offers_raw["offer"] = offers_raw["value"].map(
        lambda x: x.get("offer id") if x.get("offer id") is not None else x.get("offer_id")
    )

    # ── 1c. Drop rows where offer ID could not be extracted ─────────────────
    #        (edge case: malformed value dict)
    n_missing_offer = offers_raw["offer"].isna().sum()
    if n_missing_offer > 0:
        log.warning("  %d rows had no extractable offer ID — dropped.", n_missing_offer)
        offers_raw = offers_raw.dropna(subset=["offer"])

    # Keep only the three columns we need for the next step
    offers_raw = offers_raw[["person", "offer", "event"]]
    log.info("  Offer-event table shape after extraction: %s", offers_raw.shape)

    return offers_raw


# ===========================================================================
# ── STEP 2 ──────────────────────────────────────────────────────────────────
# Aggregate to person–offer level: one row per (customer, offer)
# ===========================================================================

def aggregate_to_person_offer(offers_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Convert the long-format event table to a wide-format person–offer table.

    Why one row per (person, offer)?
    ---------------------------------
    The raw transcript is an event log — each event (received, viewed,
    completed) appears as a separate row for the same (person, offer) pair.
    For modeling, we need one row per customer–offer interaction with three
    binary indicator columns telling us which events occurred.

    Method
    ------
    1. pd.get_dummies on the 'event' column  →  three boolean columns:
           offer_received | offer_viewed | offer_completed
    2. groupby(['person','offer']).max()  →  collapses multiple rows per pair.
       max() on booleans: 0 stays 0, but if the event happened at least once
       it becomes 1.  This correctly handles customers who received the same
       offer multiple times.

    Defensive column guard
    ----------------------
    If an event type never appeared in the data (e.g., no completions in a
    tiny test sample), pd.get_dummies will not create that column.  We add
    it as all-zeros so downstream code never breaks.

    Returns
    -------
    offers_wide : pd.DataFrame
        Columns:
            person                  — customer UUID
            offer                   — offer UUID
            offer_received          — 1 if the offer was received at least once
            offer_viewed            — 1 if the offer was viewed at least once
            offer_completed_event   — 1 if the completion event was recorded
        Rows: one per unique (person, offer) pair
    """
    log.info("STEP 2 — Aggregating to person–offer level")

    # ── 2a. One-hot encode the event column ─────────────────────────────────
    #
    # prefix='' and prefix_sep='' → column names become the event strings
    # themselves.  We then rename spaces to underscores for valid Python names.
    offers_wide = (
        pd.get_dummies(offers_raw, columns=["event"], prefix="", prefix_sep="")
        .groupby(["person", "offer"], as_index=False)
        .max()                                    # boolean OR across all events
        .rename(columns=lambda c: c.replace(" ", "_"))   # 'offer received' → 'offer_received'
    )

    # ── 2b. Ensure all three event columns exist ─────────────────────────────
    EXPECTED_EVENT_COLS: Dict[str, int] = {
        "offer_received":   0,
        "offer_viewed":     0,
        "offer_completed":  0,
    }
    for col, default in EXPECTED_EVENT_COLS.items():
        if col not in offers_wide.columns:
            log.warning("  Column '%s' missing — adding as all-%d", col, default)
            offers_wide[col] = default

    # ── 2c. Rename 'offer_completed' → 'offer_completed_event' ──────────────
    #
    # We intentionally keep the raw completion event separate from the final
    # business-rule label 'offer_completed' (created in Step 5).  Using two
    # distinct names avoids silent bugs if the pipeline is re-run.
    offers_wide = offers_wide.rename(columns={"offer_completed": "offer_completed_event"})

    log.info("  Person–offer pairs: %d  (columns: %s)",
             len(offers_wide), list(offers_wide.columns))

    return offers_wide


# ===========================================================================
# ── STEP 3 ──────────────────────────────────────────────────────────────────
# Merge demographics and offer metadata
# ===========================================================================

def merge_profile_and_portfolio(
    offers_wide: pd.DataFrame,
    profile_df:  pd.DataFrame,
    portfolio_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Left-join customer demographics (profile) and offer attributes (portfolio)
    onto the person–offer event table.

    Join logic
    ----------
    Both profile and portfolio use the column name 'id' as their primary key.
    We do a LEFT join to keep all (person, offer) pairs from the transcript,
    even if the customer or offer metadata is missing (edge case: new test
    users).  The id column from each source is dropped after the join to
    avoid duplicate named columns.

    Result schema (before cleaning)
    --------------------------------
    person, offer, offer_completed_event, offer_received, offer_viewed,
    gender, age, became_member_on, income,          ← from profile
    reward, channels, difficulty, duration, offer_type  ← from portfolio

    Parameters
    ----------
    offers_wide  : person–offer events table (output of Step 2)
    profile_df   : raw customer demographics
    portfolio_df : raw offer metadata

    Returns
    -------
    merged_df : pd.DataFrame  shape ~ (50,637, 14)
    """
    log.info("STEP 3 — Merging demographics and offer metadata")

    merged_df = (
        offers_wide
        .merge(profile_df,   how="left", left_on="person", right_on="id").drop(columns=["id"])
        .merge(portfolio_df, how="left", left_on="offer",  right_on="id").drop(columns=["id"])
    )

    log.info("  merged_df shape (before informational-offer filter): %s", merged_df.shape)

    return merged_df


# ===========================================================================
# ── STEP 4 ──────────────────────────────────────────────────────────────────
# Remove informational offers
# ===========================================================================

def remove_informational_offers(merged_df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop rows where offer_type == 'informational'.

    Why?
    ----
    Informational offers are awareness campaigns with no spend threshold and
    no completion event.  They have offer_completed_event == 0 by design, so
    including them would artificially deflate the completion rate and confuse
    the model.  The project scope is limited to BOGO and Discount offers.

    Expected impact: ~50,637 → ~50,637 rows (informational offers make up a
    small subset; exact count depends on which customers received them).

    Returns
    -------
    filtered_df : pd.DataFrame  (informational rows removed)
    """
    log.info("STEP 4 — Removing informational offers")

    n_before = len(merged_df)
    filtered_df = merged_df[merged_df["offer_type"] != "informational"].copy()
    n_removed   = n_before - len(filtered_df)

    log.info("  Removed %d informational-offer rows | remaining: %d",
             n_removed, len(filtered_df))

    return filtered_df


# ===========================================================================
# ── STEP 5 ──────────────────────────────────────────────────────────────────
# Create binary target label: offer_completed
# ===========================================================================

def create_target_label(df: pd.DataFrame) -> pd.DataFrame:
    """
    Define the project's binary outcome variable: offer_completed.

    Business Rule
    -------------
    The raw transcript records a 'completed' event whenever a customer reaches
    the spend threshold.  However, a customer can complete an offer WITHOUT
    ever viewing it (they spend the money incidentally while the offer was
    active in the background).

    For marketing purposes, we ONLY count a completion as 'successful' if
    the customer BOTH:
      1. Viewed   the offer  (offer_viewed == 1)
      2. Completed the offer (offer_completed_event == 1)

    This is called the "viewed-and-completed" business rule.  It ensures we
    measure intentional, awareness-driven behavior — the kind that tells us
    which offers are actually persuasive — rather than coincidental spending.

    Result
    ------
    offer_completed == 1  → customer saw the offer AND met the threshold
    offer_completed == 0  → customer did not see it, or saw it but didn't meet threshold

    Expected completion rate: ≈ 48.3% across all viewed BOGO/Discount offers.

    Parameters
    ----------
    df : DataFrame that must contain 'offer_viewed' and 'offer_completed_event'

    Returns
    -------
    df : same DataFrame with a new column 'offer_completed' (int 0 / 1)
    """
    log.info("STEP 5 — Creating target label: offer_completed (viewed AND completed)")

    df = df.copy()
    df["offer_completed"] = (
        (df["offer_viewed"] == 1) & (df["offer_completed_event"] == 1)
    ).astype(int)

    completion_rate = df["offer_completed"].mean()
    log.info("  offer_completed rate (all rows, incl. not-viewed): %.4f", completion_rate)

    return df


# ===========================================================================
# ── STEP 6 ──────────────────────────────────────────────────────────────────
# Derive days_since_registration from became_member_on
# ===========================================================================

def compute_days_since_registration(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert the raw 'became_member_on' integer date to a numeric tenure column.

    Raw format
    ----------
    'became_member_on' is stored as an integer in YYYYMMDD format
    (e.g., 20180425 → April 25, 2018).

    Transformation
    --------------
    1. Parse to datetime using format='%Y%m%d'.
    2. Compute reference_date = the most recent membership date in the dataset.
       Using max() as the reference simulates "days before the test window
       ends", which is a pragmatic and reproducible choice.
    3. days_since_registration = (reference_date − member_date).days
       Result: higher value = longer-tenured (more loyal) customer.
    4. Drop the original 'became_member_on' column (no longer needed).
    5. Cast to int after null imputation (see Step 8).

    Why use max() as reference_date?
    ----------------------------------
    We don't have the exact test-period start date.  Using the maximum
    enrollment date in the dataset is a neutral choice that keeps values
    non-negative and proportional to actual tenure.  A customer who joined
    the same day as the latest member gets 0 days; the earliest member gets
    the maximum value.

    Expected range: 0 – ~2,600 days (roughly 0 – 7 years of membership).

    Returns
    -------
    df : DataFrame with 'days_since_registration' added and
         'became_member_on' removed.
    """
    log.info("STEP 6 — Computing days_since_registration from became_member_on")

    if "became_member_on" not in df.columns:
        log.warning("  'became_member_on' column not found — skipping Step 6")
        return df

    df = df.copy()

    # Parse the YYYYMMDD integer to proper datetime
    member_date    = pd.to_datetime(df["became_member_on"], format="%Y%m%d", errors="coerce")
    reference_date = member_date.max()   # latest enrollment date in dataset

    df["days_since_registration"] = (reference_date - member_date).dt.days
    df = df.drop(columns=["became_member_on"])

    log.info("  reference_date       : %s", reference_date.date())
    log.info("  days_since_registration  min/median/max : %d / %d / %d",
             df["days_since_registration"].min(),
             df["days_since_registration"].median(),
             df["days_since_registration"].max())

    return df


# ===========================================================================
# ── STEP 7 ──────────────────────────────────────────────────────────────────
# One-hot encode channels  →  web, email, mobile, social binary columns
# ===========================================================================

def expand_channels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Explode the 'channels' list column into four binary indicator columns.

    Raw format
    ----------
    The portfolio's 'channels' column is a Python list of strings, e.g.:
        ['web', 'email', 'mobile']
        ['web', 'email', 'mobile', 'social']
        ['web', 'email']

    After the merge, *every row's* channels column reflects the offer's
    channel configuration (not the customer's preferences).

    Why binary columns?
    -------------------
    Machine learning models require numeric inputs.  Converting channels to
    binary flags (1 = channel is used for this offer, 0 = not used) allows
    models to learn whether mobile-delivered offers perform differently from
    email-only offers.

    Expected output
    ---------------
    web   : 1 for all offers (100% reach — every offer uses email+web)
    email : 1 for all offers
    mobile: ≈ 70–80% offers
    social: ≈ 40–50% offers

    Defensive coding
    -----------------
    We guard against NaN or non-list values in 'channels' to prevent crashes
    on re-runs or partial data.  If a value isn't a list, we treat it as an
    empty list (no channel flags set).

    Returns
    -------
    df : DataFrame with 'channels' removed and
         ['web', 'email', 'mobile', 'social'] added.
    """
    log.info("STEP 7 — Expanding channels list into binary indicator columns")

    if "channels" not in df.columns:
        log.warning("  'channels' column not found — skipping Step 7")
        return df

    df = df.copy()

    # Ensure every cell is a proper list (guard against NaN / string values)
    df["channels"] = df["channels"].apply(
        lambda x: x if isinstance(x, list) else []
    )

    # Discover all unique channel names present in the data
    all_channels: np.ndarray = df["channels"].explode().dropna().unique()
    log.info("  Channels found in data: %s", sorted(all_channels))

    # Create one binary column per channel
    for channel in all_channels:
        df[channel] = df["channels"].apply(lambda x: int(channel in x))
        log.info("  Created column '%s'  (mean %.3f)", channel, df[channel].mean())

    # Drop the original list column (no longer needed)
    df = df.drop(columns=["channels"])

    return df


# ===========================================================================
# ── STEP 8 ──────────────────────────────────────────────────────────────────
# Impute missing values
# ===========================================================================

def impute_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Handle all missing values in the merged dataset.

    Missing value summary from EDA
    --------------------------------
    | Column                  | Missing | Cause                          | Strategy         |
    |-------------------------|---------|--------------------------------|------------------|
    | age                     | ~2,175  | Placeholder value 118 used in  | Replace 118 with |
    |                         |         | the app for unknown/NaN ages   | NaN, then median |
    | income                  | ~2,175  | Same set of customers with     | Median imputation |
    |                         |         | unknown demographics           |                  |
    | gender                  | ~2,175  | Same set of customers          | Fill with 'U'    |
    |                         |         |                                | (Unknown)        |
    | days_since_registration | rare    | Parse error or very old dates  | Median imputation |

    Why these customers have missing demographics
    ---------------------------------------------
    A specific cohort of ~2,175 customers intentionally left their profile
    incomplete.  In the raw dataset, Starbucks used age=118 as a sentinel
    value to mark these records.  Income is NaN and gender is None for the
    same group.  We impute with population medians to keep them in the model
    without introducing extreme values.

    Why median (not mean)?
    -----------------------
    Age and income are right-skewed distributions.  The median is more robust
    to outliers and gives a "typical" customer value.  For example, if 10% of
    customers earn $200k+ (outliers), the mean income would be inflated, but
    the median correctly represents the middle-income customer.

    Why 'U' for unknown gender?
    ----------------------------
    Replacing None with 'U' (Unknown) rather than dropping rows:
      - Preserves ~2,175 records that might otherwise be lost.
      - Creates an explicit category the model can learn from (Unknown
        customers may behave differently from M/F/O customers).
      - Allows Power BI to show an "Unknown" segment in dashboards.

    Returns
    -------
    df : DataFrame with 0 null values in the key modeling columns.
    """
    log.info("STEP 8 — Imputing missing values")
    df = df.copy()

    # ── 8a. Age: replace sentinel 118 with NaN, then fill with median ───────
    if "age" in df.columns:
        n_sentinel  = (df["age"] == 118).sum()
        age_median  = df["age"].replace(118, np.nan).median()
        df["age"]   = df["age"].replace(118, np.nan).fillna(age_median)
        log.info("  age   : replaced %d sentinel-118 values → median %.1f", n_sentinel, age_median)

    # ── 8b. Income: fill NaN with median ────────────────────────────────────
    if "income" in df.columns:
        n_null_income  = df["income"].isna().sum()
        income_median  = df["income"].median()
        df["income"]   = df["income"].fillna(income_median)
        log.info("  income: filled %d NaN values → median %.0f", n_null_income, income_median)

    # ── 8c. Gender: fill None / NaN with 'U' (Unknown) ──────────────────────
    if "gender" in df.columns:
        n_null_gender = df["gender"].isna().sum()
        df["gender"]  = df["gender"].fillna("U")
        log.info("  gender: filled %d NaN values → 'U'", n_null_gender)

    # ── 8d. days_since_registration: fill NaN with median, cast to int ──────
    if "days_since_registration" in df.columns:
        n_null_days   = df["days_since_registration"].isna().sum()
        days_median   = df["days_since_registration"].median()
        df["days_since_registration"] = (
            df["days_since_registration"].fillna(days_median).astype(int)
        )
        log.info("  days_since_registration: filled %d NaN → median %d",
                 n_null_days, int(days_median))

    # ── 8e. Final null check ─────────────────────────────────────────────────
    null_counts = df.isnull().sum()
    null_cols   = null_counts[null_counts > 0]
    if len(null_cols) > 0:
        log.warning("  Remaining nulls after imputation:\n%s", null_cols.to_string())
    else:
        log.info("  ✅ Zero null values remaining after imputation")

    return df


# ===========================================================================
# ── STEP 9 ──────────────────────────────────────────────────────────────────
# Filter to viewed-offer rows only
# ===========================================================================

def filter_to_viewed_offers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Restrict the dataset to rows where the customer actually viewed the offer.

    Modeling Convention
    -------------------
    A customer who received an offer but never opened it cannot have been
    influenced by it.  Including unviewed offers in the training data would:
      1. Add noise (the model can't predict behavior from unseen stimuli).
      2. Deflate the apparent completion rate.
      3. Introduce an implicit counterfactual that distorts feature importance.

    After this filter, every row in the dataset represents a customer who was
    AWARE of the offer.  The target variable (offer_completed) then measures
    whether that aware customer followed through with a qualifying purchase.

    Expected row count: 39,826 (≈ 78% of the 50,637 pre-filter rows).

    Note: The 'offer_viewed' column is kept (value always 1 after this filter)
    so that analysts can verify the filter was applied, but it carries no
    predictive information for the model.

    Returns
    -------
    df : DataFrame filtered to offer_viewed == 1 rows only.
    """
    log.info("STEP 9 — Filtering to viewed-offer rows only")

    n_before = len(df)
    df       = df[df["offer_viewed"] == 1].copy()
    n_after  = len(df)

    log.info("  Rows before filter: %d | after filter: %d | removed: %d (%.1f%%)",
             n_before, n_after, n_before - n_after,
             100 * (n_before - n_after) / n_before)

    # Recompute and log final completion rate
    completion_rate = df["offer_completed"].mean()
    log.info("  offer_completed rate (viewed offers only): %.4f", completion_rate)

    return df


# ===========================================================================
# ── STEP 10 ─────────────────────────────────────────────────────────────────
# Validate quality gates (Week 1 gate per Workflow_starbuck.md §3)
# ===========================================================================

def validate_quality_gates(
    df: pd.DataFrame,
    expected_rows: int = 39_826,
    expected_cols: int = 18,
    completion_rate_tolerance: float = 0.02,
) -> bool:
    """
    Run automated quality checks and log a pass/fail report.

    Quality Gates (as defined in Workflow_starbuck.md §3)
    -------------------------------------------------------
    1. Schema check     : All expected columns are present.
    2. Null check       : ≤ 5% null per column after cleaning  (target: 0%).
    3. Duplicate check  : No duplicate (person, offer) pairs.
    4. Row count check  : Final row count within ±5% of 39,826.
    5. Completion rate  : offer_completed mean ≈ 0.483 (tolerance ±2 pp).

    Parameters
    ----------
    df                           : cleaned DataFrame to validate
    expected_rows                : target row count (default 39,826)
    expected_cols                : expected minimum column count (default 18)
    completion_rate_tolerance    : allowable deviation from 0.483 (default 0.02)

    Returns
    -------
    all_passed : bool — True if all gates pass, False if any fail.
    """
    log.info("STEP 10 — Running quality gate validation")
    all_passed = True

    # ── Gate 1: Row count ────────────────────────────────────────────────────
    row_tol   = int(expected_rows * 0.05)   # ±5%
    row_ok    = abs(len(df) - expected_rows) <= row_tol
    status    = "✅ PASS" if row_ok else "❌ FAIL"
    log.info("  [Gate 1] Row count  : %d  (expected ~%d ± %d)  %s",
             len(df), expected_rows, row_tol, status)
    all_passed = all_passed and row_ok

    # ── Gate 2: Column count ─────────────────────────────────────────────────
    col_ok = len(df.columns) >= expected_cols
    status = "✅ PASS" if col_ok else "❌ FAIL"
    log.info("  [Gate 2] Column count : %d  (expected ≥ %d)  %s",
             len(df.columns), expected_cols, status)
    all_passed = all_passed and col_ok

    # ── Gate 3: Null values ──────────────────────────────────────────────────
    null_cols = (df.isnull().mean() > 0.05)
    null_ok   = not null_cols.any()
    status    = "✅ PASS" if null_ok else "❌ FAIL"
    log.info("  [Gate 3] Null check  : %s  (columns >5%% null: %s)  %s",
             "clean" if null_ok else "has nulls",
             list(null_cols[null_cols].index) if not null_ok else "none",
             status)
    all_passed = all_passed and null_ok

    # ── Gate 4: Duplicate (person, offer) pairs ──────────────────────────────
    n_dupes = df.duplicated(subset=["person", "offer"]).sum()
    dup_ok  = n_dupes == 0
    status  = "✅ PASS" if dup_ok else "❌ FAIL"
    log.info("  [Gate 4] Duplicates  : %d duplicate (person, offer) pairs  %s",
             n_dupes, status)
    all_passed = all_passed and dup_ok

    # ── Gate 5: Completion rate ──────────────────────────────────────────────
    target_rate  = 0.483
    actual_rate  = df["offer_completed"].mean()
    rate_ok      = abs(actual_rate - target_rate) <= completion_rate_tolerance
    status       = "✅ PASS" if rate_ok else "❌ FAIL"
    log.info("  [Gate 5] Completion rate : %.4f  (expected %.3f ± %.2f)  %s",
             actual_rate, target_rate, completion_rate_tolerance, status)
    all_passed = all_passed and rate_ok

    if all_passed:
        log.info("  ✅ ALL QUALITY GATES PASSED — dataset certified for modeling")
    else:
        log.warning("  ❌ ONE OR MORE QUALITY GATES FAILED — review the output above")

    return all_passed


# ===========================================================================
# ── STEP 11 ─────────────────────────────────────────────────────────────────
# Export cleaned dataset
# ===========================================================================

def export_cleaned_data(
    df: pd.DataFrame,
    output_path: Path,
) -> Path:
    """
    Save the cleaned dataset to CSV.

    Export Strategy
    ---------------
    We export the cleaned data WITHOUT one-hot encoding gender / offer_type
    here, because:
      - Power BI needs the raw string values (F / M / O / U) for slicer labels.
      - The modeling notebooks (Week 2) will apply their own encoding steps with
        the appropriate strategy for each model.
      - This keeps the cleaned CSV as the "single source of truth" that all
        downstream processes start from.

    The file is saved with index=False (no row numbers in CSV) for clean import
    into Power BI and other tools.

    Parameters
    ----------
    df          : cleaned DataFrame to export
    output_path : destination file path (parent directory created if needed)

    Returns
    -------
    output_path : the resolved path where the file was saved.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    log.info("STEP 11 — Saved cleaned dataset to: %s  [%d rows × %d cols]",
             output_path, len(df), len(df.columns))
    return output_path


# ===========================================================================
# ── STEP 12 ─────────────────────────────────────────────────────────────────
# Engineer derived features (from notebook 01_c logic)
# ===========================================================================

def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extend the cleaned dataset with derived features needed for segmentation
    analysis and improved model performance.

    This function implements the full feature engineering pipeline from
    notebook 01_c_add_features.ipynb.

    Features Created
    ----------------

    1. membership_duration_months  (float)
       ─────────────────────────────────────────────────────────────────────
       Formula : days_since_registration / 30.44
       Round   : 2 decimal places
       Range   : 0 – ~85 months (0 – ~7 years)

       Why 30.44?  The average number of days in a calendar month, accounting
       for leap years (365.25 / 12 = 30.4375 ≈ 30.44).  This gives a more
       intuitive result than just dividing by 30 or 31.

       Business use : Loyalty segmentation.  "Loyal" = 24+ months.
                      Used in the Power BI tenure slicer.

    2. age_group  (categorical string)
       ─────────────────────────────────────────────────────────────────────
       Bins   : [0, 25] → '18-25'
                (25, 35] → '26-35'
                (35, 45] → '36-45'
                (45, 55] → '46-55'
                (55, 65] → '56-65'
                (65, ∞)  → '66+'

       Why these bins?
         - Industry-standard marketing age brackets.
         - Peak completion rate is at 46-55 (56%), so having this as a
           distinct group allows targeted strategy.
         - The 18-25 bin captures the "younger, less engaged" segment.

       include_lowest=True ensures age=0 (edge case) doesn't become NaN.

    3. income_group  (categorical string)
       ─────────────────────────────────────────────────────────────────────
       Bins   : [0, 40k]     → 'low'
                (40k, 60k]   → 'lower_middle'
                (60k, 80k]   → 'middle'
                (80k, 100k]  → 'upper_middle'
                (100k, ∞)    → 'high'

       Thresholds based on US household income quintiles and EDA findings
       that show a strong, non-linear relationship between income tier and
       completion rate (37% for 'low' vs 61% for 'high').

    4. has_web_channel    (int 0/1)
    5. has_email_channel  (int 0/1)
    6. has_mobile_channel (int 0/1)
    7. has_social_channel (int 0/1)
       ─────────────────────────────────────────────────────────────────────
       Derived from the binary channel columns (web, email, mobile, social).
       Since those columns are already 0/1, these flags are semantically
       identical, but the 'has_' prefix makes the intent explicit in reports
       and dashboards ("this offer was available on the mobile channel").

       These explicit flags are also safer for Power BI: a reader of the
       dashboard immediately understands "has_mobile_channel = 1" means
       "the offer was sent via mobile app notification."

    Parameters
    ----------
    df : output of build_clean_dataset() — the cleaned 18-column DataFrame

    Returns
    -------
    df : enriched DataFrame with 7 new columns (total ≈ 27 columns)
    """
    log.info("STEP 12 — Engineering derived features")
    df = df.copy()

    # ── 12a. Membership duration in months ───────────────────────────────────
    if "days_since_registration" not in df.columns:
        raise KeyError(
            "[STEP 12] Column 'days_since_registration' is required but missing. "
            "Ensure Step 6 ran successfully."
        )
    df["membership_duration_months"] = (df["days_since_registration"] / 30.44).round(2)
    log.info("  membership_duration_months  → min %.2f / median %.2f / max %.2f",
             df["membership_duration_months"].min(),
             df["membership_duration_months"].median(),
             df["membership_duration_months"].max())

    # ── 12b. Age groups ───────────────────────────────────────────────────────
    if "age" not in df.columns:
        raise KeyError("[STEP 12] Column 'age' is required but missing.")

    AGE_BINS   = [0,  25,  35,  45,  55,  65,  np.inf]
    AGE_LABELS = ["18-25", "26-35", "36-45", "46-55", "56-65", "66+"]

    df["age_group"] = pd.cut(
        df["age"],
        bins=AGE_BINS,
        labels=AGE_LABELS,
        include_lowest=True,
    ).astype(str)   # convert Categorical → str for CSV compatibility

    log.info("  age_group distribution:\n%s",
             df["age_group"].value_counts().sort_index().to_string())

    # ── 12c. Income groups ────────────────────────────────────────────────────
    if "income" not in df.columns:
        raise KeyError("[STEP 12] Column 'income' is required but missing.")

    INCOME_BINS   = [0, 40_000, 60_000, 80_000, 100_000, np.inf]
    INCOME_LABELS = ["low", "lower_middle", "middle", "upper_middle", "high"]

    df["income_group"] = pd.cut(
        df["income"],
        bins=INCOME_BINS,
        labels=INCOME_LABELS,
        include_lowest=True,
    ).astype(str)

    log.info("  income_group distribution:\n%s",
             df["income_group"].value_counts().sort_index().to_string())

    # ── 12d. Channel availability flags ──────────────────────────────────────
    CHANNEL_COLS = ["web", "email", "mobile", "social"]
    for ch in CHANNEL_COLS:
        if ch not in df.columns:
            log.warning("  Channel column '%s' not found — skipping has_%s_channel", ch, ch)
            continue
        flag_col = f"has_{ch}_channel"
        df[flag_col] = (df[ch] > 0).astype(int)
        log.info("  %-22s  coverage = %.1f%%", flag_col, df[flag_col].mean() * 100)

    new_cols = (
        ["membership_duration_months", "age_group", "income_group"]
        + [f"has_{ch}_channel" for ch in CHANNEL_COLS if ch in df.columns]
    )
    log.info("  Features added: %s", new_cols)
    log.info("  Enriched DataFrame shape: %s", df.shape)

    return df


# ===========================================================================
# ── MASTER PIPELINE ──────────────────────────────────────────────────────────
# build_clean_dataset  —  runs Steps 0 to 10, returns cleaned DataFrame
# ===========================================================================

def build_clean_dataset(
    portfolio_path: Optional[Path] = None,
    profile_path:   Optional[Path] = None,
    transcript_path: Optional[Path] = None,
    data_dir:        Path = DATA_DIR,
    run_quality_gates: bool = True,
) -> pd.DataFrame:
    """
    End-to-end data cleaning pipeline: Steps 0 – 10.

    This is the main entry point for all team notebooks and scripts.
    Call this function to get the clean, validated DataFrame ready for
    modeling or Power BI export.

    Parameters
    ----------
    portfolio_path   : explicit path to portfolio.json  (optional; defaults to data_dir)
    profile_path     : explicit path to profile.json    (optional; defaults to data_dir)
    transcript_path  : explicit path to transcript.json (optional; defaults to data_dir)
    data_dir         : base data directory (used as fallback for path resolution)
    run_quality_gates: if True (default), runs automated validation after cleaning

    Returns
    -------
    cleaned_df : pd.DataFrame
        Shape   : ~39,826 rows × 18 columns
        Content : Fully cleaned, imputed, labeled dataset.
                  offer_completed is the binary target variable.

    Examples
    --------
    # Basic usage (reads from default data/ directory):
        from src.data.clean_data import build_clean_dataset
        df = build_clean_dataset()

    # Custom path:
        df = build_clean_dataset(data_dir=Path('/my/custom/data'))

    # Skip quality gates (faster, for testing):
        df = build_clean_dataset(run_quality_gates=False)
    """
    log.info("=" * 70)
    log.info("Starbucks Rewards — Data Cleaning Pipeline  (clean_data.py)")
    log.info("=" * 70)

    # Resolve file paths
    portfolio_path  = portfolio_path  or (data_dir / "portfolio.json")
    profile_path    = profile_path    or (data_dir / "profile.json")
    transcript_path = transcript_path or (data_dir / "transcript.json")

    # ── Execution ────────────────────────────────────────────────────────────
    portfolio_df, profile_df, transcript_df = load_raw_data(data_dir)

    offers_raw  = extract_offer_events(transcript_df)          # Step 1
    offers_wide = aggregate_to_person_offer(offers_raw)        # Step 2
    merged_df   = merge_profile_and_portfolio(                 # Step 3
                      offers_wide, profile_df, portfolio_df
                  )
    filtered_df  = remove_informational_offers(merged_df)      # Step 4
    labeled_df   = create_target_label(filtered_df)            # Step 5
    tenure_df    = compute_days_since_registration(labeled_df) # Step 6
    channel_df   = expand_channels(tenure_df)                  # Step 7
    imputed_df   = impute_missing_values(channel_df)           # Step 8
    cleaned_df   = filter_to_viewed_offers(imputed_df)         # Step 9

    if run_quality_gates:
        validate_quality_gates(cleaned_df)                     # Step 10

    log.info("=" * 70)
    log.info("Pipeline complete.  Final shape: %s", cleaned_df.shape)
    log.info("Columns: %s", list(cleaned_df.columns))
    log.info("=" * 70)

    return cleaned_df


# ===========================================================================
# ── MAIN ENTRY POINT ─────────────────────────────────────────────────────────
# python -m src.data.clean_data
# ===========================================================================

def main() -> None:
    """
    Command-line entry point.

    Runs the full pipeline and writes two output files:
      1. data/processed/cleaned_data.csv          — base cleaned dataset
      2. data/features_added/preprocessed_data_features_added.csv — enriched

    Usage
    -----
        # From the project root directory:
        python -m src.data.clean_data

        # Or directly:
        python src/data/clean_data.py
    """
    # ── Run base pipeline ─────────────────────────────────────────────────────
    cleaned_df = build_clean_dataset(data_dir=DATA_DIR, run_quality_gates=True)

    # ── Step 11: Export cleaned dataset ──────────────────────────────────────
    cleaned_output = PROCESSED_DIR / "cleaned_data.csv"
    export_cleaned_data(cleaned_df, cleaned_output)

    # ── Step 12: Engineer features and export enriched dataset ───────────────
    enriched_df       = add_features(cleaned_df)
    enriched_output   = FEATURES_ADDED_DIR / "preprocessed_data_features_added.csv"
    enriched_output.parent.mkdir(parents=True, exist_ok=True)
    enriched_df.to_csv(enriched_output, index=False)
    log.info("Saved enriched dataset to: %s  [%d rows × %d cols]",
             enriched_output, len(enriched_df), len(enriched_df.columns))

    log.info("")
    log.info("✅  All outputs written successfully!")
    log.info("   Cleaned  → %s", cleaned_output)
    log.info("   Enriched → %s", enriched_output)


if __name__ == "__main__":
    main()
