# Starbucks Rewards Team Workflow (Expert Upgrade, A-D Tasks Preserved)

## 1) Team Setup and Working Rules

Team Members: A, B, C, D, E

Workload split: ~20% each. Everyone touches Python and Power BI. Daily Git commits are required.

Tools:
- Python (Jupyter + VS Code)
- GitHub
- Power BI Desktop
- Microsoft Teams/Zoom daily standup (15 minutes, 7 PM)

Baseline repository approach (for your cloned repo):
- Keep this repo as the working baseline.
- Use one protected integration branch: `team-final`.
- Each task is developed in short-lived branches: `feature/<owner>-<topic>`.
- Open PR to `team-final` with at least 1 reviewer.
- Merge only when checks pass and artifacts are updated.

Daily execution protocol:
- 7 PM standup: yesterday progress, today task, blockers.
- End-of-day rule: commit + push + short update in team channel.
- Every task has one owner and one reviewer.

Definition of Done (applies to every task):
- Code runs without errors.
- Notebook/script has clear markdown or docstring explanation.
- Output artifact is saved in correct folder.
- A second person can reproduce the result.

## 2) Project Folder Heritage (Clean, Scalable Structure)

Use this as the official structure for your project from now on:

```text
starbucks_reward_data_marketing/
|- data/
|  |- raw/
|  |- interim/
|  |- processed/
|  |- external/
|  |- portfolio.json
|  |- profile.json
|  |- transcript.json
|- notebooks/
|  |- 01_data_exploration_and_preprocessing.ipynb
|  |- 02_broad_model_comparison.ipynb
|  |- 03_model_deployment_and_application.ipynb
|- src/
|  |- __init__.py
|  |- data/
|  |  |- __init__.py
|  |  |- clean_data.py
|  |  |- build_features.py
|  |- models/
|  |  |- __init__.py
|  |  |- train_supervised.py
|  |  |- train_collaborative.py
|  |  |- evaluate.py
|  |  |- recommend.py
|  |- utils/
|  |  |- __init__.py
|  |  |- io.py
|  |  |- config.py
|  |- train.py
|- reports/
|  |- figures/
|  |- week1/
|  |- week2/
|  |- week3/
|- dashboards/
|  |- powerbi/
|  |  |- starbucks_rewards.pbix
|- outputs/
|  |- models/
|  |- predictions/
|  |- metrics/
|- docs/
|  |- workflow/
|  |- meeting_notes/
|- tests/
|  |- test_data_pipeline.py
|  |- test_model_pipeline.py
|- environment.yml
|- README.md
|- Workflow_starbuck.md
```

Python code location standard:
- Put all reusable Python logic in `src/`.
- Keep notebooks for analysis/storytelling, not for final production logic.
- Save final generated data to `data/processed/`.
- Save model files to `outputs/models/`.
- Save recommendation outputs to `outputs/predictions/`.

## 3) Quality Controls and Scoring Boosters

Quality gates by week:
- Week 1 gate: schema checks, null checks, duplicated ID checks, feature dictionary complete.
- Week 2 gate: baseline vs model comparison table, leakage check, calibration check.
- Week 3 gate: dashboard usability test, metric consistency check between Python and Power BI, narrative review.

Mandatory metric set:
- Classification: Accuracy, Precision, Recall, F1, ROC-AUC.
- Recommendation/business: completion lift vs random, expected revenue uplift, segment-level uplift.
- Reporting: confidence intervals for key KPI deltas when possible.

Extra-credit upgrades:
- Add RFM segmentation in preprocessing.
- Estimate CLV impact from improved completion.
- Include limitations and future work slide.
- Local market framing (Vietnam insights) where relevant.

## 4) Three-Week Plan (A-D Responsibilities Kept Intact)

### Week 1: Data Preparation + EDA
Goal: Clean data + discover insights.
Deliverable: cleaned dataset + EDA report + initial Power BI.

Day 1 (Monday)
- All 5: Download dataset and sync the baseline repository. Read both READMEs. Initialize folder structure above.
- Person A: Create shared OneDrive/Google Drive for raw files + Power BI file.
- Standup checkpoint: everyone confirms local setup and data access.

Day 2-3: Data Cleaning and Preprocessing
- Persons A + B: Run and improve `01_Data_Exploration_And_Preprocessing.ipynb` from primary repo. Merge transcript/portfolio/profile into one dataframe (offer success label: viewed + completed). Handle missing values, create `offer_completed` column.
- Persons C + D: Add new features (membership duration in months, age groups, income groups, channel flags).
- Person E: Build `src/data/clean_data.py`, define preprocessing contract, and write documentation for every cleaning step.
- Deliverable (end of Day 3):
	- `data/processed/cleaned_data.csv`
	- `reports/week1/data_cleaning_report.md`

Day 4-5: EDA and Initial Insights
- All 5: Run EDA on cleaned data.
- Persons A + C: Demographic analysis (age/gender/income vs offer success) + visualizations in Python (seaborn).
- Persons B + D: Offer performance by type/channel + transaction amount analysis.
- Person E: Start Power BI file, import cleaned CSV, create 3 basic pages (Overview, Demographics, Offer Performance), and align metric definitions with Python outputs.
- Deliverable (end of Day 5):
	- EDA notebook updates
	- Power BI v0.1 (minimum 5 visuals)
	- one-page insight summary with quantified findings

Day 6-7 (Weekend): Review and Fix
- Group review: merge approved changes into `team-final`.
- Person E: Finalize Week 1 report section with reproducible paths and charts.
- Week 1 package:
	- cleaned data
	- EDA assets
	- Power BI draft
	- 2-page insights document

### Week 2: Modeling + Evaluation (Core Recommendation Engine)
Goal: Build and compare 2 recommendation models.
Deliverable: best model + predictions CSV.

Day 8-9: Feature Engineering and Baseline
- Persons A + B: Finish feature engineering (one-hot for offer type/channel, scale numericals). Create user-offer matrix for SVD.
- Persons C + D: Train baseline (most popular offer) + Random Forest from primary repo.
- Person E: Prepare train/test split (80/20), evaluation functions (F1, Accuracy, MSE), and central metric logger in `src/models/evaluate.py`.

Day 10-12: Build Recommendation Models
- Persons A + C: Supervised model (Random Forest / Gradient Boosting) - predict completion probability per customer-offer.
- Persons B + D: Collaborative filtering model (SVD from second repo) - build user-item matrix + predict ratings.
- Person E: Hyperparameter tuning (GridSearch), model registry in `outputs/models/`, and combine both models into one function `recommend_best_offer(customer_id)`.

Day 13-14: Evaluation and Business KPIs
- All 5: Evaluate both models.
- Persons A + B: Calculate marketing KPIs (completion rate lift vs random, expected revenue uplift = reward x predicted completion).
- Persons C + D: Feature importance + error analysis.
- Person E: Export predictions (`customer_id`, `best_offer`, `probability`, `expected_revenue`) to `outputs/predictions/` for Power BI and create evaluation summary tables.
- Deliverable (end of Day 14):
	- model comparison report
	- final predictions CSV
	- 2-page evaluation report with KPI table

Day 15 (Weekend): Documentation + Git Push
- All: finalize model cards and assumptions.
- Person E: consolidate artifacts and verify reproducibility from clean clone.

### Week 3: Power BI Dashboards + Marketing Insights + Final Delivery
Goal: Production-quality dashboard + actionable strategy.

Day 16-17: Power BI Dashboard Building
- Persons A + C: Page 1 - Overview + KPIs (overall completion rate, revenue uplift simulation).
- Persons B + D: Page 2 - Customer Segments + Recommended Offers (slicer by age/gender/income).
- Person E: Page 3 - Offer Performance + Marketing Recommendations (what offer to send to whom). Add tooltips, bookmarks, drill-through, and page-level consistency checks.

Day 18-19: Business Insights and Strategies
- All 5: Analyze dashboard together.
- Persons A + B: Write 3-5 marketing strategies (example: Target 30-45 high-income males with Discount offer #7 via social media; expected +18% completion).
- Persons C + D: Simulate ROI (before/after personalization).
- Person E: Create final report (10-15 pages: executive summary, methodology, results, recommendations) + slide deck draft.

Day 20: Polish and Test
- All 5: Final review of dashboard + report. Record 2-minute Power BI demo.
- Person E: Prepare final presentation (10 slides), make sure every metric in slides matches final CSV.

Day 21: Submission and Rehearsal
- Submission package:
	- clean GitHub repo
	- Power BI `.pbix` with 3 interactive pages
	- final report PDF
	- predictions CSV
	- 10-minute presentation

## 5) Team Balance Summary (Unchanged Intent)

- Everyone does Python modeling (Week 2)
- Everyone touches Power BI (Week 1-3)
- Everyone writes insights
- Persons A + B: heavier on modeling/cleaning
- Persons C + D: heavier on visualization/insights
- Person E: coordinator + reporting, still coding daily

## 6) Immediate Next Actions (Start Now)

1. Implement the folder structure in this repository.
2. Move/keep notebooks under `notebooks/` naming standard for new files.
3. Start `src/data/clean_data.py` and `src/models/evaluate.py` as Week 1-2 backbone scripts.
4. Enforce daily PRs into `team-final` with reviewer signoff.

