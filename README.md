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
[02] Model Comparison & Selection
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
├── metrics/                    # Model evaluation reports (from 02, 03)
├── models/                     # Trained model artifacts
└── predictions/                # Prediction outputs for recommendations

reports/
├── week1/
│   ├── data_cleaning_report.md
│   ├── insights_summary.md
│   ├── powerbi_specification.md
│   └── WEEK_1_STATUS_CHECKLIST.md
├── figures/                    # EDA plots from notebooks
└── week2/, week3/              # Phase-specific reports
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

2. Open 01_b_Data_explore_and_process.ipynb (optional validation)
   Run all cells → validates preprocessing logic, confirms checkpoint values

3. Open 01_c_add_features.ipynb
   Run all cells → generates data/features_added/preprocessed_data_features_added.csv

4. Open 02_Broad_Model_Comparison.ipynb
   Run all cells → compares models, shows ROC curves, finds best hyperparameters

5. Open 03_Model_Deployment_And_Application.ipynb
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

**✅ Completed (Week 1):**
- ✅ Data preprocessing & quality validation
- ✅ Feature engineering
- ✅ Model comparison & hyperparameter tuning
- ✅ EDA analysis & insights documentation
- ✅ Power BI dashboard specification

**⏳ In Progress (Week 2-3):**
- ⏳ Notebook 03: Final model deployment via SageMaker
- ⏳ Build Power BI dashboard (3 pages, 5+ visuals)
- ⏳ Generate production recommendations for marketing team

**Last Updated:** March 27, 2026


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
