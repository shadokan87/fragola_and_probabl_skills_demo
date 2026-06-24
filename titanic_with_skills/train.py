"""Titanic: Machine Learning from Disaster — Training & Prediction Pipeline.

This script builds a classifier to predict passenger survival on the
Titanic, engineers features from the raw passenger data, trains an
ensemble model via cross-validation, and writes the submission file.

Features engineered:
    - Title extracted from Name (Mr, Mrs, Miss, Master, Rare).
    - FamilySize = SibSp + Parch + 1.
    - IsAlone flag.
    - Cabin deck (first letter of Cabin, or 'Unknown').
    - Fare and Age bins.
    - Ticket frequency (passengers sharing the same ticket).

Model:
    Stacking ensemble of HistGradientBoosting, RandomForest, and
    ExtraTrees classifiers with a LogisticRegression final estimator,
    evaluated via StratifiedKFold (5-fold) cross-validation.
"""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
    StackingClassifier,
    VotingClassifier,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


# ---------------------------------------------------------------------------
# 1. Load data
# ---------------------------------------------------------------------------
train_df = pd.read_csv("data/train.csv")
test_df = pd.read_csv("data/test.csv")

passenger_ids = test_df["PassengerId"].copy()
combined = pd.concat([train_df, test_df], axis=0, ignore_index=True)


# ---------------------------------------------------------------------------
# 2. Feature engineering (applied to the combined frame)
# ---------------------------------------------------------------------------
def extract_title(name: str) -> str:
    """Return the title from a passenger name string."""
    title = name.split(",")[1].split(".")[0].strip()
    rare = [
        "Lady", "Countess", "Capt", "Col", "Don", "Dr",
        "Major", "Rev", "Sir", "Jonkheer", "Dona",
    ]
    if title in rare:
        return "Rare"
    if title == "Mlle" or title == "Ms":
        return "Miss"
    if title == "Mme":
        return "Mrs"
    return title


combined["Title"] = combined["Name"].apply(extract_title)

# Family features
combined["FamilySize"] = combined["SibSp"] + combined["Parch"] + 1
combined["IsAlone"] = (combined["FamilySize"] == 1).astype(int)

# Cabin deck
combined["Deck"] = combined["Cabin"].apply(
    lambda x: str(x)[0] if pd.notna(x) else "Unknown"
)

# Ticket frequency (how many passengers share the same ticket)
ticket_counts = combined["Ticket"].value_counts()
combined["TicketFreq"] = combined["Ticket"].map(ticket_counts)

# Fill missing Age with median per Title
combined["Age"] = combined.groupby("Title")["Age"].transform(
    lambda x: x.fillna(x.median())
)

# Fill missing Embarked with mode, Fare with median
combined["Embarked"] = combined["Embarked"].fillna(
    combined["Embarked"].mode()[0]
)
combined["Fare"] = combined["Fare"].fillna(combined["Fare"].median())

# Age and Fare bins
combined["AgeBin"] = pd.cut(
    combined["Age"], bins=[0, 12, 20, 40, 60, 120],
    labels=["Child", "Teen", "Adult", "MidAge", "Senior"],
)
combined["FareBin"] = pd.qcut(
    combined["Fare"], q=5, labels=["VLow", "Low", "Mid", "High", "VHigh"],
    duplicates="drop",
)


# ---------------------------------------------------------------------------
# 3. Select features and split back into train / test
# ---------------------------------------------------------------------------
feature_cols = [
    "Pclass", "Sex", "Age", "SibSp", "Parch", "Fare",
    "Embarked", "Title", "FamilySize", "IsAlone", "Deck",
    "TicketFreq", "AgeBin", "FareBin",
]

train = combined.iloc[: len(train_df)].copy()
test = combined.iloc[len(train_df) :].copy()

X_train = train[feature_cols]
y_train = train["Survived"].astype(int)
X_test = test[feature_cols]


# ---------------------------------------------------------------------------
# 4. Preprocessing pipeline
# ---------------------------------------------------------------------------
numeric_features = ["Age", "SibSp", "Parch", "Fare", "FamilySize",
                    "IsAlone", "TicketFreq"]
categorical_features = ["Pclass", "Sex", "Embarked", "Title", "Deck",
                        "AgeBin", "FareBin"]

numeric_transformer = Pipeline(steps=[
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler()),
])

categorical_transformer = Pipeline(steps=[
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
])

preprocessor = ColumnTransformer(transformers=[
    ("num", numeric_transformer, numeric_features),
    ("cat", categorical_transformer, categorical_features),
])


# ---------------------------------------------------------------------------
# 5. Model — stacking ensemble
# ---------------------------------------------------------------------------
estimators = [
    ("hgb", HistGradientBoostingClassifier(
        max_iter=500,
        learning_rate=0.05,
        max_depth=5,
        min_samples_leaf=15,
        l2_regularization=1.0,
        random_state=42,
    )),
    ("rf", RandomForestClassifier(
        n_estimators=500,
        max_depth=7,
        min_samples_leaf=4,
        random_state=42,
        n_jobs=-1,
    )),
    ("et", ExtraTreesClassifier(
        n_estimators=500,
        max_depth=7,
        min_samples_leaf=4,
        random_state=42,
        n_jobs=-1,
    )),
]

stacking_clf = StackingClassifier(
    estimators=estimators,
    final_estimator=LogisticRegression(max_iter=1000, random_state=42),
    cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
    n_jobs=-1,
)

model = Pipeline(steps=[
    ("preprocessor", preprocessor),
    ("classifier", stacking_clf),
])


# ---------------------------------------------------------------------------
# 6. Cross-validation
# ---------------------------------------------------------------------------
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="accuracy")

print(f"Cross-validation accuracy: {scores.mean():.4f} (+/- {scores.std():.4f})")
print(f"Per-fold scores: {[f'{s:.4f}' for s in scores]}")


# ---------------------------------------------------------------------------
# 7. Train on full training set and predict
# ---------------------------------------------------------------------------
model.fit(X_train, y_train)
predictions = model.predict(X_test)

submission = pd.DataFrame({
    "PassengerId": passenger_ids,
    "Survived": predictions.astype(int),
})
submission.to_csv("submission.csv", index=False)

print(f"\nSubmission saved: submission.csv ({len(submission)} rows)")
print(submission.head(10))
