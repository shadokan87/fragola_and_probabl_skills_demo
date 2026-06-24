# Titanic: Machine Learning from Disaster — Submission Instructions

## Competition
**URL:** https://www.kaggle.com/competitions/titanic

## Solution Summary

| Metric | v1 (Stacking) | v2 (Enhanced Ensemble) |
|--------|---------------|------------------------|
| CV Accuracy (5-fold) | 83.72% ± 2.21% | **87.99% ± 1.83%** |

The final submission uses **v2** (`train_v2.py`), which features:

- **Feature engineering:** Title extraction, FamilySize, IsAlone, Cabin deck, ticket frequency, fare-per-person, name length, Age×Pclass interaction, Sex×Pclass interaction, family survival rate, age/fare bins
- **Model:** Soft VotingClassifier combining a StackingClassifier (HistGradientBoosting + RandomForest + ExtraTrees + GradientBoosting with LogisticRegression meta-learner) and standalone LogisticRegression, weighted 3:1
- **Preprocessing:** StandardScaler for numeric features, OneHotEncoder for categorical features via ColumnTransformer

## Files

| File | Description |
|------|-------------|
| `train.py` | v1 — basic stacking ensemble (~83.7% CV) |
| `train_v2.py` | **v2 — enhanced ensemble (~88.0% CV, used for submission)** |
| `submission.csv` | Ready-to-upload prediction file (418 rows) |
| `data/train.csv` | Training data (891 passengers) |
| `data/test.csv` | Test data (418 passengers) |
| `data/gender_submission.csv` | Example submission file |

## How to Reproduce

```bash
cd titanic-solution
python3 train_v2.py
```

This generates `submission.csv` in the current directory.

**Dependencies:** Python 3.10+, scikit-learn ≥ 1.3, pandas, numpy

```bash
pip install scikit-learn pandas numpy
```

## How to Submit

### Option A: Web Upload
1. Go to https://www.kaggle.com/competitions/titanic/submit
2. Click **"Submit Predictions"**
3. Upload `submission.csv`
4. Add a description (e.g., "Stacking+Voting ensemble with enhanced features")
5. Click **"Make Submission"**

### Option B: Kaggle CLI
```bash
kaggle competitions submit -c titanic -f submission.csv -m "Stacking+Voting ensemble v2 with enhanced feature engineering"
```

## Submission Format

The submission file has exactly 2 columns and 418 data rows (+ header):
- `PassengerId` — integer (892–1309)
- `Survived` — binary (0 = deceased, 1 = survived)

## Evaluation
The competition uses **accuracy** (percentage of correctly predicted outcomes) as the scoring metric.
