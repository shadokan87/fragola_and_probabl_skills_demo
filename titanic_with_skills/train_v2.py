"""Titanic v2 — enhanced feature engineering + voting ensemble.

Additional features over v1:
    - Name length.
    - Fare per person (Fare / TicketFreq).
    - Family survival rate (historical survival of same-surname family).
    - Interaction: Sex × Pclass.
"""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
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
n_train = len(train_df)
combined = pd.concat([train_df, test_df], axis=0, ignore_index=True)


# ---------------------------------------------------------------------------
# 2. Feature engineering
# ---------------------------------------------------------------------------
def extract_title(name: str) -> str:
    """Return the title from a passenger name string."""
    title = name.split(",")[1].split(".")[0].strip()
    title_map = {
        "Mlle": "Miss", "Ms": "Miss", "Mme": "Mrs",
        "Lady": "Rare", "Countess": "Rare", "Capt": "Rare",
        "Col": "Rare", "Don": "Rare", "Dr": "Rare",
        "Major": "Rare", "Rev": "Rare", "Sir": "Rare",
        "Jonkheer": "Rare", "Dona": "Rare",
    }
    return title_map.get(title, title)


combined["Title"] = combined["Name"].apply(extract_title)

# Family features
combined["FamilySize"] = combined["SibSp"] + combined["Parch"] + 1
combined["IsAlone"] = (combined["FamilySize"] == 1).astype(int)
combined["FamilyGroup"] = combined["FamilySize"].apply(
    lambda x: "single" if x == 1 else ("small" if x <= 4 else "large")
)

# Cabin deck
combined["Deck"] = combined["Cabin"].apply(
    lambda x: str(x)[0] if pd.notna(x) else "U"
)
combined["HasCabin"] = combined["Cabin"].notna().astype(int)

# Ticket features
ticket_counts = combined["Ticket"].value_counts()
combined["TicketFreq"] = combined["Ticket"].map(ticket_counts)

# Fill missing values
combined["Age"] = combined.groupby("Title")["Age"].transform(
    lambda x: x.fillna(x.median())
)
combined["Embarked"] = combined["Embarked"].fillna("S")
combined["Fare"] = combined["Fare"].fillna(combined["Fare"].median())

# Derived numeric features
combined["FarePerPerson"] = combined["Fare"] / combined["TicketFreq"]
combined["NameLength"] = combined["Name"].apply(len)
combined["Age*Pclass"] = combined["Age"] * combined["Pclass"]

# Sex × Pclass interaction
combined["Sex_Pclass"] = combined["Sex"] + "_" + combined["Pclass"].astype(str)

# Age bins
combined["AgeBin"] = pd.cut(
    combined["Age"], bins=[0, 5, 12, 18, 35, 60, 120],
    labels=["Baby", "Child", "Teen", "Young", "MidAge", "Senior"],
)

# Fare bins
combined["FareBin"] = pd.qcut(
    combined["Fare"], q=6, labels=False, duplicates="drop",
)


# ---------------------------------------------------------------------------
# 3. Family survival rate (from training data only to avoid leakage)
# ---------------------------------------------------------------------------
combined["Surname"] = combined["Name"].apply(lambda x: x.split(",")[0])

# Compute family survival from training data only
train_part = combined.iloc[:n_train]
family_survival = (
    train_part.groupby("Surname")["Survived"]
    .agg(["mean", "count"])
    .rename(columns={"mean": "FamilySurvivalRate", "count": "FamilyCount"})
)
# Only use families with ≥2 members to be meaningful
family_survival.loc[family_survival["FamilyCount"] < 2, "FamilySurvivalRate"] = 0.5
combined = combined.merge(
    family_survival[["FamilySurvivalRate"]],
    left_on="Surname", right_index=True, how="left",
)
combined["FamilySurvivalRate"] = combined["FamilySurvivalRate"].fillna(0.5)


# ---------------------------------------------------------------------------
# 4. Select features
# ---------------------------------------------------------------------------
feature_cols = [
    "Pclass", "Sex", "Age", "SibSp", "Parch", "Fare",
    "Embarked", "Title", "FamilySize", "IsAlone", "Deck",
    "TicketFreq", "FarePerPerson", "NameLength", "HasCabin",
    "Age*Pclass", "Sex_Pclass", "FamilyGroup", "AgeBin",
    "FareBin", "FamilySurvivalRate",
]

train = combined.iloc[:n_train].copy()
test = combined.iloc[n_train:].copy()

X_train = train[feature_cols]
y_train = train["Survived"].astype(int)
X_test = test[feature_cols]


# ---------------------------------------------------------------------------
# 5. Preprocessing
# ---------------------------------------------------------------------------
numeric_features = [
    "Age", "SibSp", "Parch", "Fare", "FamilySize", "IsAlone",
    "TicketFreq", "FarePerPerson", "NameLength", "HasCabin",
    "Age*Pclass", "FareBin", "FamilySurvivalRate",
]
categorical_features = [
    "Pclass", "Sex", "Embarked", "Title", "Deck",
    "Sex_Pclass", "FamilyGroup", "AgeBin",
]

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
# 6. Model — soft voting + stacking ensemble
# ---------------------------------------------------------------------------
hgb = HistGradientBoostingClassifier(
    max_iter=600, learning_rate=0.03, max_depth=4,
    min_samples_leaf=20, l2_regularization=1.5,
    random_state=42,
)
rf = RandomForestClassifier(
    n_estimators=600, max_depth=7, min_samples_leaf=3,
    max_features="sqrt", random_state=42, n_jobs=-1,
)
et = ExtraTreesClassifier(
    n_estimators=600, max_depth=7, min_samples_leaf=3,
    random_state=42, n_jobs=-1,
)
gb = GradientBoostingClassifier(
    n_estimators=400, learning_rate=0.05, max_depth=4,
    min_samples_leaf=15, subsample=0.8, random_state=42,
)
lr = LogisticRegression(
    C=1.0, max_iter=1000, solver="lbfgs", random_state=42,
)

# Stacking ensemble
stacking_clf = StackingClassifier(
    estimators=[("hgb", hgb), ("rf", rf), ("et", et), ("gb", gb)],
    final_estimator=LogisticRegression(
        C=0.5, max_iter=1000, random_state=42
    ),
    cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
    n_jobs=-1,
    passthrough=False,
)

# Voting ensemble (average stacking + LR)
voting_clf = VotingClassifier(
    estimators=[("stacking", stacking_clf), ("lr", lr)],
    voting="soft",
    weights=[3, 1],
    n_jobs=-1,
)

model = Pipeline(steps=[
    ("preprocessor", preprocessor),
    ("classifier", voting_clf),
])


# ---------------------------------------------------------------------------
# 7. Cross-validation
# ---------------------------------------------------------------------------
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="accuracy")

print(f"Cross-validation accuracy: {scores.mean():.4f} (+/- {scores.std():.4f})")
print(f"Per-fold scores: {[f'{s:.4f}' for s in scores]}")


# ---------------------------------------------------------------------------
# 8. Train on full data and predict
# ---------------------------------------------------------------------------
model.fit(X_train, y_train)
predictions = model.predict(X_test)

submission = pd.DataFrame({
    "PassengerId": passenger_ids,
    "Survived": predictions.astype(int),
})
submission.to_csv("submission.csv", index=False)

print(f"\nSubmission saved: submission.csv ({len(submission)} rows)")
print(submission["Survived"].value_counts())
