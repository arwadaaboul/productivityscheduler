"""
train_model.py
--------------
Trains three Random Forest classifiers and saves them as .pkl files.

  Model A: real survey data only     -> models/model_real.pkl
  Model B: synthetic dataset only    -> models/model_synthetic.pkl
  Model C: both datasets combined    -> models/model_combined.pkl

Run from the Project root:
    python app/model/train_model.py
"""

import os
import sys
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.utils import resample
import pandas as pd

# ── Path setup ────────────────────────────────────────────────────────────────
PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_DIR)

from app.utils.preprocess import load_real, load_synthetic, load_combined

MODELS_DIR = os.path.join(PROJECT_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)


# ── Balance classes via upsampling (handles small dataset imbalance) ──────────

def balance_classes(X, y):
    """Upsample minority classes to match the majority class count."""
    df = X.copy()
    df["_label"] = y.values

    classes = df["_label"].unique()
    max_count = df["_label"].value_counts().max()

    balanced_parts = []
    for cls in classes:
        cls_df = df[df["_label"] == cls]
        upsampled = resample(cls_df, replace=True, n_samples=max_count, random_state=42)
        balanced_parts.append(upsampled)

    balanced = pd.concat(balanced_parts).sample(frac=1, random_state=42)
    X_bal = balanced.drop(columns=["_label"])
    y_bal = balanced["_label"]
    return X_bal, y_bal


# ── Training function ─────────────────────────────────────────────────────────

def train_and_save(name, load_fn, save_path):
    """Train one RandomForest model and save it. Returns accuracy."""
    print(f"\n{'='*55}")
    print(f"  Training {name}")
    print(f"{'='*55}")

    X, y, feature_names = load_fn()
    print(f"  Rows: {len(X)}  |  Features: {feature_names}")
    print(f"  Class distribution:\n{y.value_counts().to_string()}")

    # Balance classes before splitting
    X_bal, y_bal = balance_classes(X, y)

    X_train, X_test, y_train, y_test = train_test_split(
        X_bal, y_bal, test_size=0.2, random_state=42, stratify=y_bal
    )

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        min_samples_split=2,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    print(f"\n  Accuracy: {acc:.2%}")
    print(f"\n  Classification Report:\n{classification_report(y_test, y_pred)}")

    # Save model + metadata together
    payload = {
        "model": model,
        "feature_names": feature_names,
        "accuracy": acc,
        "name": name,
    }
    joblib.dump(payload, save_path)
    print(f"  Saved → {save_path}")
    return acc


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    results = {}

    results["Model A – Real Survey"] = train_and_save(
        name="Model A – Real Survey Only",
        load_fn=load_real,
        save_path=os.path.join(MODELS_DIR, "model_real.pkl"),
    )

    results["Model B – Synthetic"] = train_and_save(
        name="Model B – Synthetic Dataset Only",
        load_fn=load_synthetic,
        save_path=os.path.join(MODELS_DIR, "model_synthetic.pkl"),
    )

    results["Model C – Combined"] = train_and_save(
        name="Model C – Combined (Real + Synthetic)",
        load_fn=load_combined,
        save_path=os.path.join(MODELS_DIR, "model_combined.pkl"),
    )

    print(f"\n{'='*55}")
    print("  ACCURACY COMPARISON SUMMARY")
    print(f"{'='*55}")
    for model_name, acc in results.items():
        bar = "█" * int(acc * 30)
        print(f"  {model_name:35s}  {acc:.2%}  {bar}")
    print(f"{'='*55}\n")
    print("✅ All models trained and saved in /models/")

