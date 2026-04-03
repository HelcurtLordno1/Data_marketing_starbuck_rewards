# Starbucks Reward Data Marketing - Updated Workflow Status

Last updated: 2026-04-03

This document reflects the current project state after the latest notebook rework, including:
- refreshed preprocessing notebooks,
- marketing-focused EDA,
- premodel pipeline with temporal split,
- collaborative ranking diagnostics,
- exported artifacts for modeling and dashboarding.

## 1) Current Project Scope

Primary objective:
- Predict offer success and generate actionable customer-offer recommendations for marketing execution.

Key data sources:
- `data/portfolio.json`
- `data/profile.json`
- `data/transcript.json`

Core workflow:
1. Data preprocessing and feature engineering
2. Marketing EDA and playbook insights
3. Premodel split, baseline modeling, threshold strategy
4. Ranking diagnostics and artifact export

## 2) Active Notebook Pipeline (Current)

Main notebooks in active sequence:
1. `notebooks/01_a_Data_Exploration_And_Preprocessing.ipynb`
2. `notebooks/01_b_rework_preprocess.ipynb`
3. `notebooks/01_c_add_new.ipynb`
4. `notebooks/02_a_eda_clean.ipynb`
5. `notebooks/02_b_premodel_steps_rework.ipynb`
6. `notebooks/02_Broad_Model_Comparison.ipynb` (downstream modeling)
7. `notebooks/03_Model_Deployment_And_Application.ipynb` (deployment/application)

Notes:
- Legacy notebooks `01_b_Data_explore_and_process.ipynb` and `01_c_add_features.ipynb` have been replaced by rework versions.
- `02_b_premodel_steps_rework.ipynb` is now the active premodel reference notebook.

## 3) What Has Been Updated

### 3.1 Preprocessing and feature generation

Implemented and validated:
- robust merge of transcript/profile/portfolio,
- target engineering (`offer_success`) from offer journey logic,
- missing-value handling with explicit flags,
- channel and offer one-hot features,
- behavioral and value features,
- export to processed and feature-added datasets.

Main generated datasets:
- `data/processed/preprocessed_data.csv`
- `data/processed/preprocessed_data_rework_marketing.csv`
- `data/features_added/preprocessed_data_features_added.csv`

### 3.2 EDA and marketing insights

`02_a_eda_clean.ipynb` includes:
- demographic and segment diagnostics,
- offer/channel performance analysis,
- spend and tenure patterns,
- funnel and readiness checks,
- actionable marketing playbook section.

### 3.3 Premodel strategy (major change)

Critical improvement in `02_b_premodel_steps_rework.ipynb`:
- split changed from group holdout to `Per-User Leave-Last Temporal Split`.

Why this matters:
- each validation row is a realistic next-offer prediction,
- user history is preserved in training,
- avoids the prior cold-start failure mode for collaborative filtering,
- aligns with business deployment logic (train on past, predict next action).

### 3.4 Ranking diagnostics added

A dedicated ranking section was added to compare:
- `hist_gb` (best supervised model),
- `most_popular_offer` baseline,
- `svd_collaborative`.

Ranking metrics used:
- `ndcg@3`, `ndcg@5`,
- `recall@3`, `recall@5`.

Positioning of SVD in this project:
- proves collaborative signal exists,
- serves as ranking baseline,
- contributes diversity for ensemble strategies,
- not expected to be strongest standalone classifier with only 8 offers and high sparsity.

## 4) Current Artifact Outputs

Premodel exports (latest run):
- `outputs/premodel/train_split.csv`
- `outputs/premodel/valid_split_with_preds.csv`
- `outputs/premodel/baseline_model_scores.csv`
- `outputs/premodel/threshold_sweep.csv`
- `outputs/premodel/premodel_config.json`

## 5) Latest Performance Snapshot

From current premodel exports:

Classification metrics (validation):
- `hist_gb`: accuracy 0.8291, f1 0.7886, roc_auc 0.9073, pr_auc 0.8213
- `random_forest`: accuracy 0.8006, f1 0.7467, pr_auc 0.7884
- `log_reg`: accuracy 0.7890, f1 0.7591, pr_auc 0.7690
- `most_popular_offer`: accuracy 0.6581, f1 0.4603, pr_auc 0.5100
- `svd_collaborative`: roc_auc 0.5387, pr_auc ~0.404 (ranking signal present, weak classifier at threshold 0.5)

Threshold strategy:
- selected best operating point: `best_threshold = 0.475` (for best supervised model).

Ranking sanity check (top-level interpretation):
- supervised model remains strongest ranker,
- popularity baseline is competitive,
- SVD is useful as a collaborative benchmark and ensemble component.

## 6) Reproducible Run Order (Recommended)

To fully regenerate current outputs:
1. Run `01_b_rework_preprocess.ipynb`
2. Run `01_c_add_new.ipynb`
3. Run `02_a_eda_clean.ipynb`
4. Run `02_b_premodel_steps_rework.ipynb` from top to bottom

Expected outcomes after step 4:
- refreshed `outputs/premodel/*` files,
- updated baseline model comparison table,
- threshold sweep and config snapshot,
- ranking diagnostics table (NDCG/Recall@K).

## 7) Quality and Governance Notes

Current quality controls in notebook process:
- explicit leakage-column drops,
- deterministic temporal split logic with order checks,
- train/valid overlap diagnostics,
- model comparison under one preprocessing contract,
- segment-level performance diagnostics.

Known practical caveats:
- with small offer catalog size and sparse interactions, SVD should be interpreted primarily for ranking baseline value, not high binary classification lift at fixed threshold.

## 8) Suggested Next Improvements

Recommended next actions for production-grade refinement:
1. Add per-user ranking metrics to exported artifacts (NDCG@K, Recall@K tables).
2. Calibrate probability outputs for campaign decision thresholds by segment.
3. Add time-based backtesting windows (rolling evaluation) for stability checks.
4. Feed SVD/popularity scores into supervised meta-model for hybrid ranking.
5. Align Power BI KPI pages to the latest temporal split outputs.
