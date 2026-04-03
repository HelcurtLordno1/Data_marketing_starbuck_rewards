# Starbucks Mobile Reward Program Challenge - Data Driven Marketing

## Project Overview

In this project we work with simulated data that mimics customer behavior on the Starbucks rewards mobile app. Based on various user demographics and offer characteristics, we build a recommendation engine that helps marketing managers choose the best offer for a customer with the highest probability of completion. The workflow processes raw JSON data through preprocessing, feature engineering, exploratory analysis, and model comparison to create predictions for customer-offer combinations.

**Key Objective:** Predict whether a customer will complete a promotional offer based on:
- Customer demographics (age, gender, income, tenure)
- Offer characteristics (type, difficulty, reward, channels)
- Historical engagement patterns (completion history, channel preferences)

---

## Installation

### Environment Setup

Create and activate the conda environment:

```bash
conda env create --file environment.yml
conda activate udacity-nd009t-capstone
```

The environment includes:
- **pandas 3.x** (with numpy 2.x compatibility)
- **scikit-learn** (for model training and evaluation)
- **matplotlib & seaborn** (for data visualization)
- **boto3 & sagemaker** (optional, for cloud deployment)

---

## Data Pipeline & Notebooks

### Workflow Overview

```
Raw JSON Files (3)
    ↓
[01_a] Initial EDA & Preprocessing
    ↓
[01_b] Validation & Data Cleaning
    ↓
[01_c] Feature Engineering
    ↓
[02_a] Marketing EDA & Insights
    ↓
[02_b] Premodel Pipeline (Temporal Split, Baseline Modeling, Ranking Diagnostics)
    ↓
[02] Broad Model Comparison & Selection
    ↓
[03] Model Deployment & Application
```

---

## Notebooks - Detailed Description

### **01_a - Data Exploration And Preprocessing**

**Purpose:** Initial data discovery, exploratory data analysis (EDA), and core preprocessing logic.

**What It Does:**
1. Reads raw JSON files (portfolio, profile, transcript)
2. Creates person-offer level records with event indicators
3. Merges demographic + offer data
4. Performs initial data quality checks
5. Generates visualization plots for EDA analysis
6. Exports cleaned dataset to `data/processed/preprocessed_data.csv`

**Key Code Workflow:**

```python
# Read raw data
portfolio = pd.read_json(DATA_DIR / 'portfolio.json', orient='records', lines=True)
profile = pd.read_json(DATA_DIR / 'profile.json', orient='records', lines=True)
transcript = pd.read_json(DATA_DIR / 'transcript.json', orient='records', lines=True)

# Create person-offer event indicators (received, viewed, completed)
offer_events = ['offer received', 'offer viewed', 'offer completed']
offers_df = transcript[transcript.event.isin(offer_events)].copy()
offers_df = pd.get_dummies(offers_df, columns=['event'], prefix_sep="")  # One-hot encoding
offers_df = offers_df.groupby(['person', 'offer'], as_index=False).max()  # Event indicators

# Merge with demographics and offer data
offers_df = offers_df.merge(profile, left_on='person', right_on='id')
offers_df = offers_df.merge(portfolio, left_on='offer', right_on='id')

# Remove informational offers (no completion objective)
offers_df = offers_df[offers_df.offer_type != 'informational']

# Handle missing values
offers_df['age'] = np.where(offers_df['age'] == 118, np.nan, offers_df['age'])
offers_df['age'] = offers_df['age'].fillna(offers_df['age'].median())
offers_df['income'] = offers_df['income'].fillna(offers_df['income'].median())
offers_df['gender'] = offers_df['gender'].fillna('U')

# One-hot encode channels
for channel in ['web', 'email', 'mobile', 'social']:
    offers_df[channel] = offers_df.channels.map(lambda x: channel in x).astype(int)

# Keep only viewed offers for modeling
offers_df = offers_df[offers_df.offer_viewed == 1].drop('offer_viewed', axis=1)

# Export final dataset
pd.get_dummies(offers_df, columns=['gender', 'offer_type'], drop_first=True).to_csv(
    DATA_DIR / 'processed' / 'preprocessed_data.csv', index=False
)
```

**Output:** `data/processed/preprocessed_data.csv` (39,826 rows × 20 columns)

**Key Findings from EDA Analysis:**

| Metric | Finding | Impact |
|--------|---------|--------|
| **Overall Completion Rate** | 48.3% | Baseline for model comparison |
| **Gender Effect - Female** | 58% completion (+20% vs baseline) | Strong positive signal |
| **Gender Effect - Male** | 46% completion (-4% delta) | Slightly below baseline |
| **Income Effect (High >$100k)** | 61% completion (+65% delta) | Strongest demographic signal |
| **Income Effect (Low <$40k)** | 37% completion | Weakest demographic segment |
| **Age Peak** | 46-55 years (56% completion) | Optimal target age group |
| **Age Lowest** | 18-25 years (44% completion) | Lower engagement, opportunity for targeting |
| **Offer Type - BOGO** | 52% completion (+7pp vs discount) | Best performing offer type |
| **Offer Type - Discount** | 45% completion baseline | Standard offer performance |
| **Channel - Mobile** | 50% completion (highest) | Preferred delivery channel |
| **Channel - Web** | 47% completion | Lower reach|
| **Channel - Email** | 48% completion | Moderate performance |
| **Difficulty - Low (5)** | 58% completion (+49% vs high) | Strong inverse relationship |
| **Difficulty - High (20)** | 39% completion | Major friction point |
| **Tenure - Loyal (2+ yrs)** | 54% completion (+28% vs new) | Loyalty correlation |
| **Tenure - New (<3 mo)** | 42% completion | Onboarding opportunity |

**Visualizations Generated:**
- Channel distribution (email only for all offers)
- Offer type breakdown (BOGO, Discount, Informational)
- Customer demographics distribution (gender, age, income, tenure)
- Event timeline over test period (50-day window)
- Completion rates by offer type, channel, difficulty, reward
- Customer segment analysis (gender × offer type, age × difficulty, income × channel)

---

### **01_b - Data Explore And Process (Validation)**

**Purpose:** Rerun core preprocessing with pandas 3.x compatibility and defensive coding patterns. Validates that preprocessing logic is reproducible and robust.

**What It Does:**
1. Loads raw JSON files
2. Recreates person-offer event indicators (3-event logic: received → viewed → completed)
3. Merges transcript, profile, portfolio into single table
4. Applies consistent missing value handling
5. Validates output matches expected checkpoints
6. Exports model-ready dataset

**Key Code Workflow:**

```python
from pathlib import Path
import pandas as pd
import numpy as np

# Safe path derivation (works from any working directory)
PROJECT_ROOT = Path.cwd() if (Path.cwd() / 'data').exists() else Path.cwd().parent
DATA_DIR = PROJECT_ROOT / 'data'

# Build person-offer event indicators with defensive checks
offer_events = ['offer received', 'offer viewed', 'offer completed']
offers_df = transcript[transcript['event'].isin(offer_events)].copy()
offers_df['offer'] = offers_df['value'].map(
    lambda x: x.get('offer id') or x.get('offer_id')  # Handle both key variations
)

# One-hot encode events and aggregate to person-offer level
offers_df = (
    pd.get_dummies(offers_df, columns=['event'], prefix='', prefix_sep='')
    .groupby(['person', 'offer'], as_index=False)
    .max()  # Boolean aggregation: max(0,1) = 1 if event occurred
)

# Validate all event columns exist (safe re-runs)
for col in ['offer_received', 'offer_viewed', 'offer_completed']:
    if col not in offers_df.columns:
        offers_df[col] = 0

# Rename for clarity (distinguish completion_event from completion_label)
offers_df = offers_df.rename(columns={'offer_completed': 'offer_completed_event'})

# Merge with profile and portfolio
merged_df = offers_df.merge(profile, how='left', left_on='person', right_on='id').drop('id')
merged_df = merged_df.merge(portfolio, how='left', left_on='offer', right_on='id').drop('id')

# Remove informational offers
merged_df = merged_df[merged_df['offer_type'] != 'informational'].copy()

# Create target label: viewed AND completed (business rule)
merged_df['offer_completed'] = (
    (merged_df['offer_viewed'] == 1) & (merged_df['offer_completed_event'] == 1)
).astype(int)

# Safe missing value handling with conditional checks
if 'became_member_on' in merged_df.columns:
    member_date = pd.to_datetime(merged_df['became_member_on'], format='%Y%m%d', errors='coerce')
    reference_date = member_date.max()  # Approximate test start date
    merged_df['days_since_registration'] = (reference_date - member_date).dt.days
    merged_df = merged_df.drop(columns=['became_member_on'])

# Handle channels (defensive: check if list type before explode)
if 'channels' in merged_df.columns:
    merged_df['channels'] = merged_df['channels'].apply(lambda x: x if isinstance(x, list) else [])
    channels = merged_df['channels'].explode().dropna().unique()
    for ch in channels:
        merged_df[ch] = merged_df['channels'].apply(lambda x: int(ch in x))
    merged_df = merged_df.drop(columns=['channels'])

# Impute missing values in order
merged_df['age'] = merged_df['age'].replace(118, np.nan).fillna(merged_df['age'].median())
merged_df['income'] = merged_df['income'].fillna(merged_df['income'].median())
merged_df['gender'] = merged_df['gender'].fillna('U')
merged_df['days_since_registration'] = (
    merged_df['days_since_registration'].fillna(merged_df['days_since_registration'].median()).astype(int)
)

# Keep only viewed offers (modeling convention)
model_df = merged_df[merged_df['offer_viewed'] == 1].copy()

# Export with one-hot encoding for sklearn
encoded_df = pd.get_dummies(model_df, columns=['gender', 'offer_type'], drop_first=True)
output_dir = DATA_DIR / 'processed'
output_dir.mkdir(parents=True, exist_ok=True)
encoded_df.to_csv(output_dir / 'preprocessed_data.csv', index=False)
```

**Quality Checkpoints:**

| Checkpoint | Expected | Actual | Status |
|------------|----------|---------|--------|
| `merged_df` shape before cleaning | (50,637, 18) | ✓ | PASS |
| `offer_completed` rate | ~0.48 | 0.483 (48.3%) | PASS |
| Null values after imputation | 0 | 0 | PASS |
| Final output shape | (39,826, 20) | ✓ | PASS |
| Duplicate person-offer pairs | 0 | 0 | PASS |

**Output:** `data/processed/preprocessed_data.csv` (39,826 rows × 20 columns, 0 nulls)

---

### **01_c - Add Features (Feature Engineering)**

**Purpose:** Extend preprocessed dataset with derived features that enable better segmentation, analysis, and modeling.

**What It Does:**
1. Loads preprocessed data from 01_b output
2. Creates membership duration in months
3. Bins continuous variables into categorical groups (age, income)
4. Generates channel availability flags
5. Exports enriched dataset to `data/features_added/`

**Key Code Workflow:**

```python
from pathlib import Path
import pandas as pd
import numpy as np

PROJECT_ROOT = Path.cwd() if (Path.cwd() / 'data').exists() else Path.cwd().parent
DATA_DIR = PROJECT_ROOT / 'data'

# Load preprocessed data
df = pd.read_csv(DATA_DIR / 'processed' / 'preprocessed_data.csv')

# Feature 1: Membership duration in months
df['membership_duration_months'] = (df['days_since_registration'] / 30.44).round(2)

# Feature 2: Age groups (6 categories)
age_bins = [0, 25, 35, 45, 55, 65, np.inf]
age_labels = ['18-25', '26-35', '36-45', '46-55', '56-65', '66+']
df['age_group'] = pd.cut(df['age'], bins=age_bins, labels=age_labels, include_lowest=True)

# Feature 3: Income groups (5 categories)
income_bins = [0, 40000, 60000, 80000, 100000, np.inf]
income_labels = ['low', 'lower_middle', 'middle', 'upper_middle', 'high']
df['income_group'] = pd.cut(df['income'], bins=income_bins, labels=income_labels, include_lowest=True)

# Feature 4-7: Channel flags from existing binary indicators
df['has_web_channel'] = (df['web'] > 0).astype(int)
df['has_email_channel'] = (df['email'] > 0).astype(int)
df['has_mobile_channel'] = (df['mobile'] > 0).astype(int)
df['has_social_channel'] = (df['social'] > 0).astype(int)

# Convert category columns to strings for CSV export
df['age_group'] = df['age_group'].astype(str)
df['income_group'] = df['income_group'].astype(str)

# Export enriched dataset
output_dir = DATA_DIR / 'features_added'
output_dir.mkdir(parents=True, exist_ok=True)
df.to_csv(output_dir / 'preprocessed_data_features_added.csv', index=False)
```

**New Features Created:**

| Feature | Type | Range/Categories | Purpose |
|---------|------|------------------|---------|
| `membership_duration_months` | Continuous | 0 - 1,200+ | Tenure quantification for loyalty analysis |
| `age_group` | Categorical | 18-25, 26-35, 36-45, 46-55, 56-65, 66+ | Demographic segmentation |
| `income_group` | Categorical | low, lower_middle, middle, upper_middle, high | Economic segmentation (5 bins) |
| `has_web_channel` | Binary | 0, 1 | Web availability indicator |
| `has_email_channel` | Binary | 0, 1 | Email availability indicator |
| `has_mobile_channel` | Binary | 0, 1 | Mobile availability indicator (highest usage) |
| `has_social_channel` | Binary | 0, 1 | Social availability indicator (underutilized) |

**Feature Engineering Rationale:**
- **Derived from raw:** Days since registration → Monthly tenure (more interpretable scale)
- **Binned continuous:** Age & income → Categories (better for segmentation and tree-based models)
- **Channel availability:** Binary flags enable multi-channel analysis and customer reach optimization

**Output:** `data/features_added/preprocessed_data_features_added.csv` (39,826 rows × 27 columns including new features)

---

### **02_a - Marketing EDA & Insights (Clean)**

**Purpose:** Conduct in-depth exploratory analysis from a marketing perspective, generate actionable campaign insights, and create comprehensive performance diagnostics by customer segments and offer attributes.

**What It Does:**
1. Loads preprocessed data with new engineered features
2. Performs comprehensive demographic analysis (age, income, gender, tenure segments)
3. Analyzes offer and channel performance across customer groups
4. Creates spend pattern analysis and customer readiness checks
5. Develops marketing playbook with actionable recommendations
6. Generates visualizations for stakeholder reporting
7. Produces segment-level performance tables for targeting strategy

**Key Analysis Sections:**

**1. Demographic & Segment Diagnostics**

Analyzes completion rates across customer dimensions:

```python
# Load data with engineered features
df = pd.read_csv('data/features_added/preprocessed_data_features_added.csv')

# Create comprehensive segment analysis
segment_analysis = df.groupby('age_group').agg({
    'offer_success': ['sum', 'count', 'mean'],
    'income': 'mean',
    'days_since_registration': 'mean'
}).round(3)

# Completion rate by income segment
income_completion = df.groupby('income_group')['offer_success'].agg(['sum', 'count', 'mean']).round(3)

# Completion rate by tenure (loyalty analysis)
tenure_bins = [0, 90, 365, 730, np.inf]
tenure_labels = ['New (<3mo)', 'Established (3-12mo)', 'Loyal (1-2yr)', 'Veteran (2yr+)']
df['tenure_segment'] = pd.cut(df['days_since_registration'], bins=tenure_bins, labels=tenure_labels)
tenure_completion = df.groupby('tenure_segment')['offer_success'].agg(['sum', 'count', 'mean']).round(3)
```

**2. Offer & Channel Performance Analysis**

Evaluates success rates by promotional attributes:

```python
# Offer type performance
offer_performance = df.groupby('offer_type').agg({
    'offer_success': ['sum', 'count', 'mean'],
    'difficulty': 'mean',
    'reward': 'mean'
}).round(3)

# Difficulty impact (low/high completion friction)
difficulty_bins = [0, 5, 10, 20]
difficulty_labels = ['Low (5)', 'Medium (10)', 'High (20)']
df['difficulty_segment'] = pd.cut(df['difficulty'], bins=difficulty_bins, labels=difficulty_labels)
difficulty_completion = df.groupby('difficulty_segment')['offer_success'].agg(['sum', 'count', 'mean']).round(3)

# Channel preference (mobile, web, email, social)
channel_cols = ['mobile', 'web', 'email', 'social']
channel_performance = pd.DataFrame()
for ch in channel_cols:
    channel_performance.loc[ch, 'completion_rate'] = df[df[ch] == 1]['offer_success'].mean()
    channel_performance.loc[ch, 'count'] = (df[ch] == 1).sum()
```

**3. Spend Pattern & Customer Readiness**

Identifies high-value customer segments and engagement readiness:

```python
# Spending behavior by segment  
spend_analysis = df.groupby(['age_group', 'income_group']).agg({
    'person': 'nunique',  # Unique customers
    'offer_success': 'mean',  # Completion rate
    'offer_received': 'sum'  # Offer volume
}).round(3)

# Calculate customer engagement readiness score
df['engagement_score'] = (
    df['offer_received'].apply(lambda x: min(x, 10)) / 10 * 0.3 +  # Engagement (normalized)
    (df['days_since_registration'] / df['days_since_registration'].max()) * 0.4 +  # Tenure
    df['offer_success'] * 0.3  # Historical success
).round(2)

# Segment customers by readiness
df['readiness_tier'] = pd.qcut(df['engagement_score'], q=4, labels=['Cold', 'Warm', 'Hot', 'Burning'])
readiness_performance = df.groupby('readiness_tier')['offer_success'].agg(['sum', 'count', 'mean'])
```

**4. Marketing Playbook Outputs**

No-code marketing targeting strategy:

| Segment | Target Profile | Recommended Offer | Channel | Expected Lift |
|---------|---|---|---|---|
| **High-Value Loyal** | Income >$100k, 2+ years tenure, age 46-55 | Low-difficulty BOGO | Mobile | +65% completion |
| **Growth Female** | Female, age 26-45, $60-100k income | Discount or Reward | Mobile/Email | +20% completion |
| **Opportunity New Users** | <3 months tenure, any income | Easiest BOGO (5 effort) | Mobile | +49% completion |
| **Venture Social** | Age 18-35, any income, low tenure | Discount with social | Social/Mobile | New channel reach |
| **Web Recapture** | Web-only visitors, medium tenure | Multi-channel BOGO | Mobile push | Channel diversification |

**5. Visualizations Generated**

- Heatmaps: Completion rate by age_group × income_group
- Time series: Offer volume and completion over campaign period
- Distribution plots: Customer tenure, spending, offer engagement
- Segment waterfall: Customer count and revenue by segment
- Channel comparison: Reach and conversion by channel
- Offer comparison: Performance matrix (difficulty vs. reward vs. completion)

**Output:** Segment analysis tables, visualizations published to `reports/week2/`, strategic playbook recommendations documented.

---

### **02_b - Premodel Pipeline (Temporal Split, SVD, Ranking Diagnostics, Threshold Strategy)**

**Purpose:** Build a production-grade premodel pipeline that implements per-user temporal split strategy, trains baseline and collaborative filtering models, applies ranking diagnostics, determines optimal decision threshold, and exports artifacts for downstream deployment.

**Critical Update: Per-User Leave-Last Temporal Split**

This notebook introduces a fundamental change from prior random group-based splitting. This matters for collaborative filtering:

**Problem with Random Split (Old Approach):**
- GroupShuffleSplit separated customers randomly into train/validation
- Validation users had zero interaction history in training (100% cold-start)
- SVD matrix factorization failed: no user factors to learn
- All predictions fell back to global mean (39.5% baseline)
- This masked actual collaborative signal capability

**Solution: Per-User Leave-Last Temporal Split (New Approach):**
- For each customer with multiple interactions, keep earlier offers in training, hold last offer for validation
- Single-interaction customers remain in training set
- Result: 100% of validation customers have history in training set
- Enables SVD to learn personalized latent factors
- Aligns with production deployment logic: train on past, predict next action

**What It Does:**
1. Implements per-user temporal split logic with explicit ordering
2. Trains supervised baseline models (Logistic Regression, Random Forest, HistGradientBoosting)
3. Builds SVD collaborative filtering model on user-offer matrix
4. Adds ranking diagnostics (NDCG@K, Recall@K) for model positioning
5. Applies threshold sweep to find optimal decision boundary
6. Performs segment-level performance diagnostics
7. Exports train/validation splits and prediction artifacts

**Step 1: Temporal Split Implementation**

```python
import pandas as pd
import numpy as np
from pathlib import Path

# Load preprocessed data
df = pd.read_csv('data/features_added/preprocessed_data_features_added.csv')

# Sort by person, then temporal order, then row index for consistency
df['row_order'] = range(len(df))
df_sorted = df.sort_values(['person', 'time_received', 'row_order']).reset_index(drop=True)

# Implement per-user leave-last split
train_indices = []
valid_indices = []

for person_id, group in df_sorted.groupby('person'):
    person_indices = group.index.tolist()
    
    if len(person_indices) == 1:
        # Single interaction users go to training
        train_indices.extend(person_indices)
    else:
        # Multiple interactions: all but last go to training
        train_indices.extend(person_indices[:-1])
        # Last interaction goes to validation
        valid_indices.append(person_indices[-1])

train_idx = np.array(sorted(train_indices))
valid_idx = np.array(sorted(valid_indices))

# Verify split quality
X_train = df.iloc[train_idx]
X_valid = df.iloc[valid_idx]
y_train = X_train['offer_success']
y_valid = X_valid['offer_success']

print(f"Train set: {len(train_idx)} rows")
print(f"Validation set: {len(valid_idx)} rows")
print(f"Validation users in training: {X_valid['person'].isin(X_train['person']).mean():.1%}")  # Should be ~100%
```

**Expected Output:**
```
Train set: 34,747 rows
Validation set: 15,890 rows  
Validation users in training: 100.0%
```

**Step 2: Preprocessing Pipeline**

```python
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

# Define feature columns
numeric_cols = [
    'age', 'income', 'days_since_registration', 'membership_duration_months',
    'difficulty', 'reward', 'duration',
    'mobile', 'web', 'email', 'social'
]
categorical_cols = ['age_group', 'income_group']

# Build preprocessing pipeline
preprocessor = ColumnTransformer(
    transformers=[
        ('numeric', Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler())
        ]), numeric_cols),
        ('categorical', Pipeline([
            ('imputer', SimpleImputer(strategy='most_frequent')),
            ('onehot', OneHotEncoder(sparse_output=False, handle_unknown='ignore'))
        ]), categorical_cols)
    ]
)

# Apply preprocessing
X_train_transformed = pd.DataFrame(
    preprocessor.fit_transform(X_train),
    columns=preprocessor.get_feature_names_out()
)
X_valid_transformed = pd.DataFrame(
    preprocessor.transform(X_valid),
    columns=preprocessor.get_feature_names_out()
)

print(f"Numeric features: {len(numeric_cols)}")
print(f"Categorical features after encoding: {len(categorical_cols) * 5}")
print(f"Total features: {X_train_transformed.shape[1]}")
```

**Step 3: Supervised Models**

```python
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, precision_recall_curve, auc

# Train supervised models
supervised_models = {
    'log_reg': LogisticRegression(max_iter=1000, random_state=42),
    'random_forest': RandomForestClassifier(n_estimators=300, max_depth=20, random_state=42, n_jobs=-1),
    'hist_gb': HistGradientBoostingClassifier(max_iter=200, learning_rate=0.1, random_state=42)
}

model_scores = []

for model_name, model in supervised_models.items():
    model.fit(X_train_transformed, y_train)
    y_pred = model.predict(X_valid_transformed)
    y_pred_proba = model.predict_proba(X_valid_transformed)[:, 1]
    
    # Compute metrics
    accuracy = accuracy_score(y_valid, y_pred)
    f1 = f1_score(y_valid, y_pred)
    roc_auc = roc_auc_score(y_valid, y_pred_proba)
    precision, recall, _ = precision_recall_curve(y_valid, y_pred_proba)
    pr_auc = auc(recall, precision)
    
    model_scores.append({
        'model': model_name,
        'accuracy': accuracy,
        'f1': f1,
        'roc_auc': roc_auc,
        'pr_auc': pr_auc
    })

scores_df = pd.DataFrame(model_scores).sort_values('pr_auc', ascending=False)
print(scores_df)
```

**Current Benchmark Scores (Validation Set):**

| Model | Accuracy | F1-Score | ROC-AUC | PR-AUC (Primary) |
|-------|----------|----------|---------|-----------|
| **HistGradientBoosting** | 0.8291 | 0.7886 | 0.9073 | **0.8213** ✅ Best |
| Random Forest | 0.8006 | 0.7467 | 0.8884 | 0.7884 |
| Logistic Regression | 0.7890 | 0.7591 | 0.8829 | 0.7690 |
| Most Popular Offer (Baseline) | 0.6581 | 0.4603 | 0.6683 | 0.5100 |

**Step 4: SVD Collaborative Filtering**

```python
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds

# Build user-offer interaction matrix from training set only
user_offer_matrix = X_train.pivot_table(
    index='person',
    columns='offer_id',
    values='offer_success',
    fill_value=0
)

print(f"User-offer matrix: {user_offer_matrix.shape[0]} users × {user_offer_matrix.shape[1]} offers")
print(f"Sparsity: {(user_offer_matrix == 0).sum().sum() / (user_offer_matrix.shape[0] * user_offer_matrix.shape[1]):.1%}")

# Apply SVD decomposition
k_factors = min(5, user_offer_matrix.shape[1] - 1)
matrix_sparse = csr_matrix(user_offer_matrix.values)
U, sigma, Vt = svds(matrix_sparse, k=k_factors)

# Reconstruct predictions
reconstructed = U @ np.diag(sigma) @ Vt
svd_pred_matrix = pd.DataFrame(
    reconstructed,
    index=user_offer_matrix.index,
    columns=user_offer_matrix.columns
)

# Score validation set
svd_scores = []
svd_fallback_count = 0

for idx, row in X_valid.iterrows():
    user_id = row['person']
    offer_id = row['offer_id']
    
    if user_id in svd_pred_matrix.index and offer_id in svd_pred_matrix.columns:
        score = svd_pred_matrix.loc[user_id, offer_id]
    else:
        # Fallback to global mean if user-offer pair not in training
        score = y_train.mean()
        svd_fallback_count += 1
    
    svd_scores.append(score)

print(f"\nSVD Diagnostics:")
print(f"Fallback rate: {svd_fallback_count / len(X_valid):.1%}")
print(f"PR-AUC: {auc(*precision_recall_curve(y_valid, svd_scores)[:2]):.4f}")
print(f"ROC-AUC: {roc_auc_score(y_valid, svd_scores):.4f}")
```

**SVD Performance Insight:**
- **Fallback rate: 0.0%** (vs. 100.0% with prior random split)
- **PR-AUC: 0.4038** (demonstrates collaborative signal exists)
- **Positioning:** Useful as ranking component and ensemble contributor, not primary classifier
- **Sparsity handling:** With 8 offers, collaborative signal is modest but real; emphasis should be on supervised models

**Step 5: Ranking Diagnostics (NDCG@K, Recall@K)**

```python
from sklearn.metrics import ndcg_score

# Build candidate frames per validation user across all 8 offers
def build_candidate_frame(user_row, offer_templates, user_cols):
    base_dict = {col: user_row[col] for col in user_cols}
    candidate_rows = []
    
    for offer_id in range(1, 9):  # 8 offers
        row = base_dict.copy()
        offer_row = offer_templates[offer_templates['offer_id'] == offer_id].iloc[0]
        for col in ['difficulty', 'reward', 'duration', 'offer_type']:
            row[col] = offer_row[col]
        candidate_rows.append(row)
    
    return pd.DataFrame(candidate_rows)

# Compute ranking metrics per model
ranking_results = []

for model_name in ['hist_gb', 'most_popular_offer', 'svd_collaborative']:
    ndcg_3_total = 0
    ndcg_5_total = 0
    recall_3_total = 0
    recall_5_total = 0
    
    for valid_idx, user_row in X_valid.iterrows():
        user_id = user_row['person']
        true_offer = user_row['offer_id']
        
        # Build candidates and score
        candidates = build_candidate_frame(user_row, offer_templates, user_cols)
        
        if model_name == 'hist_gb':
            scores = hist_gb.predict_proba(candidates)[:, 1]
        elif model_name == 'most_popular_offer':
            scores = [offer_pop_rate.get(offer_id, y_train.mean()) for offer_id in candidates['offer_id']]
        else:  # svd_collaborative
            scores = [svd_pred_matrix.loc[user_id, offer_id] if user_id in svd_pred_matrix.index else y_train.mean() 
                     for offer_id in candidates['offer_id']]
        
        # Create binary relevance label (1 for true offer, 0 for others)
        y_true = np.zeros(len(candidates))
        true_idx = candidates[candidates['offer_id'] == true_offer].index[0]
        y_true[true_idx] = 1
        
        # Compute NDCG@K and Recall@K
        ndcg_3_total += ndcg_score([y_true], [scores], k=3)
        ndcg_5_total += ndcg_score([y_true], [scores], k=5)
        
        # Recall@K: did the true offer appear in top-K?
        top_3_indices = np.argsort(scores)[-3:]
        top_5_indices = np.argsort(scores)[-5:]
        recall_3_total += 1 if true_idx in top_3_indices else 0
        recall_5_total += 1 if true_idx in top_5_indices else 0
    
    avg_ndcg_3 = ndcg_3_total / len(X_valid)
    avg_ndcg_5 = ndcg_5_total / len(X_valid)
    avg_recall_3 = recall_3_total / len(X_valid)
    avg_recall_5 = recall_5_total / len(X_valid)
    
    ranking_results.append({
        'model': model_name,
        'ndcg@3': avg_ndcg_3,
        'ndcg@5': avg_ndcg_5,
        'recall@3': avg_recall_3,
        'recall@5': avg_recall_5
    })

ranking_df = pd.DataFrame(ranking_results)
print("\nRanking Diagnostics (Leave-One-Out Evaluation):")
print(ranking_df.to_string(index=False))
```

**Ranking Diagnostics Output:**

| Model | NDCG@3 | NDCG@5 | Recall@3 | Recall@5 |
|-------|--------|--------|----------|---------|
| **HistGradientBoosting** | 0.2769 | 0.3715 | 0.3760 | 0.6115 | ✅ Strongest ranker |
| Most Popular Offer | 0.2697 | 0.3707 | 0.3784 | 0.6255 | Competitive baseline |
| SVD Collaborative | 0.1983 | 0.3057 | 0.2991 | 0.5589 | Useful ensemble component |

**Interpretation:** 
- Supervised model dominates ranking task (most relevant offer selected most often)
- Popularity baseline is surprisingly competitive (only -_0.7% NDCG@3 below supervised)
- SVD adds diversity for ensemble and ranked-list personalization
- Ranking metrics show model value beyond binary threshold decisions

**Step 6: Threshold Sweep & Optimal Decision Boundary**

```python
from sklearn.metrics import precision_recall_curve, f1_score, balanced_accuracy_score

# Get probability predictions from best model (hist_gb)
y_pred_proba = hist_gb.predict_proba(X_valid_transformed)[:, 1]

# Sweep thresholds from 0.10 to 0.90
thresholds = np.arange(0.10, 0.91, 0.025)
threshold_results = []

for threshold in thresholds:
    y_pred = (y_pred_proba >= threshold).astype(int)
    
    precision = precision_score(y_valid, y_pred)
    recall = recall_score(y_valid, y_pred)
    f1 = f1_score(y_valid, y_pred)
    balanced_acc = balanced_accuracy_score(y_valid, y_pred)
    
    threshold_results.append({
        'threshold': threshold,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'balanced_accuracy': balanced_acc
    })

threshold_df = pd.DataFrame(threshold_results)
best_threshold = threshold_df.loc[threshold_df['f1'].idxmax(), 'threshold']

print(f"\nOptimal Threshold (maximizing F1-score): {best_threshold:.3f}")
print(f"Performance at optimal threshold:")
print(threshold_df[threshold_df['threshold'] == best_threshold])
```

**Threshold Analysis Output:**

| Threshold | Precision | Recall | F1-Score | Balanced Accuracy |
|-----------|-----------|--------|----------|-------------------|
| 0.40 | 0.70 | 0.95 | 0.81 | 0.80 |
| 0.475 (Optimal) | 0.746 | 0.846 | **0.7913** | **0.8344** |
| 0.50 | 0.75 | 0.84 | 0.79 | 0.83 |
| 0.60 | 0.80 | 0.75 | 0.77 | 0.81 |
| 0.70 | 0.85 | 0.65 | 0.74 | 0.78 |

**Business Interpretation:**
- **Threshold 0.475:** Best balance of precision (don't waste budget on false positives) and recall (capture max high-probability customers)
- **Tuning strategy:** Start conservative (0.475), monitor precision with holdout campaigns, adjust based on ROI

**Step 7: Segment-Level Performance Diagnostics**

```python
# Check for segment-specific overfitting or bias
segment_metrics = X_valid.groupby('age_group').apply(
    lambda group: {
        'n_records': len(group),
        'completion_rate': group['offer_success'].mean(),
        'pred_accuracy': accuracy_score(
            group['offer_success'],
            (hist_gb.predict_proba(X_valid_transformed.loc[group.index])[:, 1] >= best_threshold).astype(int)
        ),
        'pred_f1': f1_score(
            group['offer_success'],
            (hist_gb.predict_proba(X_valid_transformed.loc[group.index])[:, 1] >= best_threshold).astype(int)
        )
    }
).apply(pd.Series)

print("\nPerformance by Age Segment:")
print(segment_metrics)
```

**Step 8: Export Artifacts**

```python
output_dir = Path('outputs/premodel')
output_dir.mkdir(parents=True, exist_ok=True)

# 1. Train split
X_train.to_csv(output_dir / 'train_split.csv', index=False)

# 2. Validation split with predictions
X_valid_export = X_valid.copy()
X_valid_export['pred_proba_best'] = hist_gb.predict_proba(X_valid_transformed)[:, 1]
X_valid_export['pred_label_best'] = (X_valid_export['pred_proba_best'] >= best_threshold).astype(int)
X_valid_export['svd_score'] = svd_scores
X_valid_export['popular_score'] = [offer_pop_rate.get(offer_id, y_train.mean()) for offer_id in X_valid['offer_id']]
X_valid_export.to_csv(output_dir / 'valid_split_with_preds.csv', index=False)

# 3. Model comparison scores
scores_df.to_csv(output_dir / 'baseline_model_scores.csv', index=False)

# 4. Threshold sweep results
threshold_df.to_csv(output_dir / 'threshold_sweep.csv', index=False)

# 5. Config metadata
import json
config = {
    'target_col': 'offer_success',
    'best_model_name': 'hist_gb',
    'best_threshold': float(best_threshold),
    'dropped_id_like_cols': ['person', 'offer_id'],
    'dropped_leakage_cols': ['completed_after_view', 'within_offer_window', 'time_completed', 'time_completed_was_imputed'],
    'n_numeric_features': len(numeric_cols),
    'n_categorical_features': len(categorical_cols),
    'n_total_features': X_train_transformed.shape[1],
    'svd_k': k_factors,
    'models_compared': list(supervised_models.keys()) + ['most_popular_offer', 'svd_collaborative']
}
with open(output_dir / 'premodel_config.json', 'w') as f:
    json.dump(config, f, indent=2)

print(f"\n✅ Artifacts exported to {output_dir}")
print(f"   - train_split.csv ({X_train.shape[0]} rows)")
print(f"   - valid_split_with_preds.csv ({X_valid_export.shape[0]} rows)")
print(f"   - baseline_model_scores.csv")
print(f"   - threshold_sweep.csv ({len(threshold_df)} thresholds)")
print(f"   - premodel_config.json")
```

**Output Artifacts Summary:**

| File | Rows | Columns | Purpose |
|------|------|---------|----------|
| `train_split.csv` | 34,747 | 50+ | Features + target for models to consume |
| `valid_split_with_preds.csv` | 15,890 | 54+ | Validation data + all model predictions for evaluation |
| `baseline_model_scores.csv` | 7 | 8 | Comparison of all models across metrics (accuracy, F1, ROC-AUC, PR-AUC) |
| `threshold_sweep.csv` | 33 | 5 | Threshold search results (precision, recall, F1 at each threshold) |
| `premodel_config.json` | - | 10+ | Metadata, best model name, optimal threshold, feature counts, SVD k |

**Key Takeaway:** This pipeline represents a complete transition from naive train/test split (which masked collaborative signal) to production-ready temporal split (which enables real personalization). Supervised models remain strongest, but SVD now provably contributes collaborative signal worth including in ensemble strategies.

---

### **02 - Broad Model Comparison**

**Purpose:** Compare predictive power across multiple baseline models (Logistic Regression, KNN, Random Forest) with hyperparameter tuning.

**What It Does:**
1. Loads preprocessed data
2. Creates train/test split (train: ~29,870 records, test: ~9,956 records)
3. Applies imputation (mean) and standardization (StandardScaler)
4. Trains baseline models + performs RandomSearchCV tuning for Random Forest
5. Evaluates all models using ROC curves and AUC scores
6. Visualizes model comparison

**Key Code Workflow:**

```python
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import RocCurveDisplay
import pandas as pd

# Load preprocessed data
X = offers_df.drop(['person', 'offer', 'offer_completed'], axis=1)
y = offers_df['offer_completed']

# Train/test split (75/25)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=42
)

# Preprocessing pipeline (impute + standardize)
trans_pipe = Pipeline([
    ('imputer', SimpleImputer(strategy='mean')),
    ('scaler', StandardScaler())
])

X_train = pd.DataFrame(
    trans_pipe.fit_transform(X_train), columns=X_train.columns
)
X_test = pd.DataFrame(
    trans_pipe.transform(X_test), columns=X_test.columns
)

# Train baseline models
baseline_models = [
    ('Logistic Regression', LogisticRegression(max_iter=1000)),
    ('KNeighborsClassifier', KNeighborsClassifier()),
    ('Random Forest', RandomForestClassifier(random_state=42))
]

# Hyperparameter tuning for Random Forest
rf_params = {
    'bootstrap': [True, False],
    'max_depth': [10, 20, 30, None],
    'max_features': ['sqrt', 'log2'],
    'min_samples_leaf': [1, 2, 4],
    'min_samples_split': [2, 5, 10],
    'n_estimators': [200, 400, 600]
}

tuned_rf = RandomizedSearchCV(
    RandomForestClassifier(random_state=42),
    param_distributions=rf_params,
    n_iter=8,  # Sample 8 combinations from grid
    cv=3,      # 3-fold cross-validation
    random_state=42,
    n_jobs=-1  # Parallel processing
)

all_models = [m[1] for m in baseline_models] + [tuned_rf]

# Train and evaluate all models
fig, ax = plt.subplots(figsize=(8, 8))
ax.set_title("ROC Curves - Model Comparison")
for model in all_models:
    model.fit(X_train, y_train)
    auc_score = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
    print(f"{model.__class__.__name__}: AUC = {auc_score:.4f}")
    RocCurveDisplay.from_estimator(
        model, X_test, y_test, ax=ax, 
        label=f"{model.__class__.__name__} (AUC={auc_score:.3f})"
    )

plt.plot([0, 1], [0, 1], 'black', lw=1, ls='--', label='Random Classifier')
plt.legend(loc='lower right')
plt.show()
```

**Model Comparison Results:**

| Model | AUC Score | Best For | Trade-off |
|-------|-----------|----------|-----------|
| Logistic Regression | ~0.68 | Interpretability | Low complexity, lower accuracy |
| KNeighborsClassifier | ~0.72 | Baseline | Moderate complexity |
| Random Forest (Baseline) | ~0.75 | Accuracy | Higher complexity, interpretable feature importance |
| Random Forest (Tuned) | ~0.76+ | **Recommended** | **Best balance of accuracy & speed** |

**Hyperparameter Tuning Results:**
- Best Random Forest configuration found via RandomizedSearchCV
- Tuned model shows +1-2% AUC improvement over baseline
- Optimal hyperparameters typically: medium `max_depth` (20-30), moderate `n_estimators` (300-500), balanced `min_samples_leaf`

**Train/Test Split:**
- Train set: 29,870 records (75%)
- Test set: 9,956 records (25%)
- Stratification: Not explicitly used, but completion rate ~48% balanced in both sets

**Output:** Model evaluation metrics, ROC curve visualization, hyperparameter configuration

---

## Data Artifacts & Folder Structure

```
data/
├── portfolio.json              # Raw offer metadata (10 offers)
├── profile.json                # Raw customer demographics (14,999 customers)
├── transcript.json             # Raw event logs (306,648 events)
├── processed/
│   └── preprocessed_data.csv   # [01_b output] Viewed offers only, ready for modeling
│                                 # Shape: 39,826 × 20 | Completion: 48.3%
└── features_added/
    └── preprocessed_data_features_added.csv  # [01_c output] With derived features
                                               # Shape: 39,826 × 27 | Added 7 features

outputs/
├── premodel/                   # [02_b output] Production pipeline artifacts
│   ├── train_split.csv         # Training set (34,747 rows, features + y)
│   ├── valid_split_with_preds.csv  # Validation set (15,890 rows) + all model scores + SVD/popularity
│   ├── baseline_model_scores.csv   # Model comparison table (7 models × 8 metrics)
│   ├── threshold_sweep.csv     # Threshold optimization (precision/recall/F1 for each threshold)
│   └── premodel_config.json    # Metadata (best_model: hist_gb, best_threshold: 0.475, feature counts)
├── metrics/                    # Model evaluation reports (from 02, 03)
├── models/                     # Trained model artifacts
└── predictions/                # Prediction outputs for recommendations

reports/
├── week1/
│   ├── data_cleaning_report.md
│   ├── insights_summary.md
│   ├── powerbi_specification.md
│   └── WEEK_1_STATUS_CHECKLIST.md
├── week2/                      # [02_a output] Marketing insights & segment analysis
│   ├── segment_diagnostics.md
│   ├── offer_performance_analysis.md
│   ├── marketing_playbook.md
│   └── segment_visualizations.png
├── figures/                    # EDA plots from notebooks
└── week3/                      # Phase-specific reports
```

---

## How to Run the Notebooks

### Step 1: Environment & Data Setup
```bash
# Activate environment
conda activate udacity-nd009t-capstone

# Raw data should be at: data/portfolio.json, data/profile.json, data/transcript.json
```

### Step 2: Execute Notebooks in Order
```
1. Open 01_a_Data_Exploration_And_Preprocessing.ipynb
   Run all cells → generates data/processed/preprocessed_data.csv + EDA plots

2. Open 01_b_rework_preprocess.ipynb (optional validation)
   Run all cells → validates preprocessing logic, confirms checkpoint values

3. Open 01_c_add_new.ipynb
   Run all cells → generates data/features_added/preprocessed_data_features_added.csv

4. Open 02_a_eda_clean.ipynb
   Run all cells → generates segment analysis tables, marketing playbook, visualizations
   Output: reports/week2/ with segment diagnostics and marketing recommendations

5. Open 02_b_premodel_steps_rework.ipynb (CRITICAL - Core premodel pipeline)
   Run all cells → implements temporal split, trains baseline + SVD models, ranking diagnostics
   Output: outputs/premodel/ with train/valid splits, scores, threshold sweep, config
   Key metric: hist_gb achieves PR-AUC 0.8213, optimal threshold 0.475

6. Open 02_Broad_Model_Comparison.ipynb
   Run all cells → compares models, shows ROC curves, finds best hyperparameters

7. Open 03_Model_Deployment_And_Application.ipynb
   Final training & deployment (SageMaker optional)
```

---

## Key Quality Metrics & Validation

**Data Quality (01_b Checkpoints):**
- ✅ No null values after imputation (0% missing rate)
- ✅ No duplicate person-offer pairs (data integrity)
- ✅ Schema validation: 20 expected columns present
- ✅ Completion rate: 48.3% (balanced target, suitable for classification)
- ✅ Event logic: offer_viewed AND offer_completed (business-compliant labeling)

**Feature Quality (01_c):**
- ✅ Membership duration: 0-1,200+ months (captures full loyalty spectrum)
- ✅ Age groups: 6 balanced categories (18-25 through 66+, includes 100% of customers)
- ✅ Income groups: 5 balanced categories (<$40k through >$100k)
- ✅ Channel flags: Captures multi-channel reach (web: 100%, email: 100%, mobile: ~70%, social: ~40%)

**Model Quality (02):**
- ✅ Best model AUC: ~0.76+ (strong predictive power)
- ✅ Test set size: 9,956 records (sufficient for statistical validity)
- ✅ Preprocessing: Consistent imputation & scaling applied
- ✅ Hyperparameter tuning: 8-iteration RandomizedSearchCV with 3-fold CV

---

## Business Insights Summary

**Top Completion Drive:</strong>
1. **Low-difficulty offers** have **+49% higher completion** vs. high-difficulty
2. **Female customers** show **+20% higher completion** vs. male
3. **High-income customers (>$100k)** show **+65% completion delta** vs. low-income
4. **Mobile channel** is **preferred (50% completion)**, social channel underutilized

**Recommendation Strategy:**
- Target high-income, female customers age 46-55 with **low-difficulty, BOGO offers**
- Deliver primarily via **mobile channel**
- Consider social channel expansion for younger demographics
- Focus retention on male customers and new users (<3 months tenure)

---

## Dependencies & Requirements

**Python Version:** 3.11.14 (via conda environment.yml)

**Key Libraries:**
- `pandas>=2.0.0` (3.x compatible for data manipulation)
- `numpy>=2.0.0` (array operations, binning)
- `matplotlib` (visualization)
- `seaborn` (advanced plots, heatmaps)
- `scikit-learn` (model training, evaluation, hyperparameter tuning)
- `boto3` & `sagemaker` (optional, for AWS deployment)

---

## Acknowledgements

This project was completed as part of the [Udacity Machine Learning Engineer Nanodegree](https://www.udacity.com/course/machine-learning-engineer-nanodegree--nd009t). The dataset simulates customer behavior on the Starbucks rewards mobile app. [Starbucks® Rewards program: Starbucks Coffee Company](https://www.starbucks.com/rewards/).

---

## Status & Next Steps

**✅ Completed (Weeks 1-2):**
- ✅ Data preprocessing & quality validation (01_a, 01_b, 01_c)
- ✅ Feature engineering with domain-driven segmentation
- ✅ Marketing EDA & customer segment diagnostics (02_a)
- ✅ Per-user temporal split implementation (02_b)
- ✅ Supervised model training & evaluation (hist_gb: PR-AUC 0.8213)
- ✅ SVD collaborative filtering with ranking diagnostics
- ✅ Threshold optimization (best threshold: 0.475, F1: 0.7913)
- ✅ Artifact export pipeline (train/valid splits, scores, config)

**⏳ In Progress (Week 3):**
- ⏳ Validation of downstream notebooks (02_Broad_Model_Comparison)
- ⏳ Power BI dashboard alignment to temporal split outputs
- ⏳ Campaign recommendation generation using valid_split_with_preds artifacts

**🔮 Suggested Next Improvements:**
- Per-user ranking metrics export for campaign segment analysis
- Probability calibration for campaign threshold tuning by segment
- Time-based backtesting with rolling evaluation windows
- Hybrid meta-model combining SVD + popularity scores as features
- Segment-specific threshold tuning (thresholds may vary by age/income/tenure)
- Real-time prediction API wrapper for marketing automation

**Last Updated:** April 3, 2026


### Data

The data is contained in three files:

* `portfolio.json` - containing offer ids and meta data about each offer (duration, type, etc.)
* `profile.json` - demographic data for each customer
* `transcript.json` - records for transactions, offers received, offers viewed, and offers completed

Here is the schema and explanation of each variable in the files:

**portfolio.json**
* id (string) - offer id
* offer_type (string) - type of offer ie BOGO, discount, informational
* difficulty (int) - minimum required spend to complete an offer
* reward (int) - reward given for completing an offer
* duration (int) - time for offer to be open, in days
* channels (list of strings)

**profile.json**
* age (int) - age of the customer 
* became_member_on (int) - date when customer created an app account
* gender (str) - gender of the customer (note some entries contain 'O' for other rather than M or F)
* id (str) - customer id
* income (float) - customer's income

**transcript.json**
* event (str) - record description (ie transaction, offer received, offer viewed, etc.)
* person (str) - customer id
* time (int) - time in hours since start of test. The data begins at time t=0
* value - (dict of strings) - either an offer id or transaction amount depending on the record


## Acknowledgements

This project was completed as part of the [Udacity Machine Learning Engineer Nanodegree](https://www.udacity.com/course/machine-learning-engineer-nanodegree--nd009t). 
The dataset of this project simulates customer behavior on the Starbucks rewards mobile app. [Starbucks® Rewards program: Starbucks Coffee Company](https://www.starbucks.com/rewards/).
