"""
ReflectSort — Member 2 (Kuldeep Singh): ML Training Pipeline
Course: Machine Learning – Embedded Systems Design (ML-ESD)
Team: ML-ESD-TEAM-117 | Project ID: PROJECT-12-VARIANT-06

Trains the reproducible grain shade classification model on synthetic
demonstration data or user-supplied labelled CSV readings.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent
DEFAULT_DATA_PATH = ROOT / "data" / "demo_data_simulated.csv"
DEFAULT_MODEL_PATH = ROOT / "model" / "shade_model.joblib"
DEFAULT_OUTPUTS_DIR = ROOT / "outputs"

FEATURES = ["sample_LDR", "ambient_LDR", "reflectance_ratio"]
TARGET = "shade_label"


def train_model(
    data_path: Path = DEFAULT_DATA_PATH,
    model_output_path: Path = DEFAULT_MODEL_PATH,
    outputs_dir: Path = DEFAULT_OUTPUTS_DIR,
    random_seed: int = 117,
) -> dict:
    """
    Train the standard ReflectSort shade classification pipeline.

    Returns the trained model bundle dictionary.
    """
    if not data_path.is_absolute():
        data_path = ROOT / data_path
    if not data_path.exists():
        raise FileNotFoundError(f"Training dataset not found: {data_path}")

    df = pd.read_csv(data_path)
    required = FEATURES + [TARGET]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in dataset: {missing}. Required: {required}")

    df = df.dropna(subset=required).copy()
    if "specimen_id" not in df.columns:
        raise ValueError("Dataset must include 'specimen_id' so repeated readings are grouped without data leakage.")

    X = df[FEATURES]
    y = df[TARGET].astype(str)
    groups = df["specimen_id"]

    # Grouped split: keep specimen repetitions strictly in train or test
    split = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=random_seed)
    train_idx, test_idx = next(split.split(X, y, groups))

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", RandomForestClassifier(
            n_estimators=150,
            class_weight="balanced",
            random_state=random_seed,
        )),
    ])

    X_train, y_train = X.iloc[train_idx], y.iloc[train_idx]
    X_test, y_test = X.iloc[test_idx], y.iloc[test_idx]

    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    accuracy = float(accuracy_score(y_test, y_pred))
    macro_f1 = float(f1_score(y_test, y_pred, average="macro"))
    classes = list(pipeline.named_steps["classifier"].classes_)

    data_source_label = "SIMULATED" if set(df.get("data_source", pd.Series(["UNKNOWN"])).astype(str)) == {"SIMULATED"} else "USER_SUPPLIED"

    bundle = {
        "pipeline": pipeline,
        "features": FEATURES,
        "classes": classes,
        "training_min": {c: float(X_train[c].min()) for c in FEATURES},
        "training_max": {c: float(X_train[c].max()) for c in FEATURES},
        "data_source": data_source_label,
        "training_seed": random_seed,
        "target": TARGET,
    }

    # Ensure output directories exist
    model_output_path.parent.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    # Save model artifact
    joblib.dump(bundle, model_output_path)

    # Save evaluation artifacts
    cls_report_str = (
        f"DATA SOURCE: {bundle['data_source']}\n"
        f"Accuracy: {accuracy:.4f}\nMacro-F1: {macro_f1:.4f}\n\n"
        + classification_report(y_test, y_pred, zero_division=0)
    )
    (outputs_dir / "classification_report.txt").write_text(cls_report_str, encoding="utf-8")

    cm = confusion_matrix(y_test, y_pred, labels=classes)
    pd.DataFrame(cm, index=classes, columns=classes).to_csv(outputs_dir / "confusion_matrix.csv")

    summary = {
        "data_source": bundle["data_source"],
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "features": FEATURES,
        "classes": classes,
        "training_min": bundle["training_min"],
        "training_max": bundle["training_max"],
        "split": "specimen_id grouped 75/25",
        "training_seed": random_seed,
        "warning": "Synthetic-data metrics are software checks only, not real-world performance.",
    }
    (outputs_dir / "evaluation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    report_md = (
        f"# ReflectSort ML Training & Evaluation Report\n\n"
        f"- **Data Source:** {bundle['data_source']} (Simulated optical reflectance)\n"
        f"- **Random Seed:** {random_seed}\n"
        f"- **Accuracy (Validation Group Split):** {accuracy:.4f} ({accuracy * 100:.2f}%)\n"
        f"- **Macro-F1:** {macro_f1:.4f}\n"
        f"- **Feature List:** `{FEATURES}`\n"
        f"- **Target Classes:** `{classes}`\n\n"
        f"### Training Ranges\n"
        + "\n".join([f"- **`{c}`:** {bundle['training_min'][c]:.4f} to {bundle['training_max'][c]:.4f}" for c in FEATURES])
        + "\n\n> [!NOTE]\n> Synthetic dataset metrics validate software execution and feature pipelines. They do not represent physical hardware field accuracy.\n"
    )
    (outputs_dir / "training_evaluation_report.md").write_text(report_md, encoding="utf-8")

    return bundle


def main():
    parser = argparse.ArgumentParser(description="Train ReflectSort ML model")
    parser.add_argument("--data", default=str(DEFAULT_DATA_PATH), help="Path to training CSV")
    parser.add_argument("--output", default=str(DEFAULT_MODEL_PATH), help="Path to save trained joblib model bundle")
    parser.add_argument("--outputs-dir", default=str(DEFAULT_OUTPUTS_DIR), help="Directory to save evaluation reports")
    args = parser.parse_args()

    bundle = train_model(
        data_path=Path(args.data),
        model_output_path=Path(args.output),
        outputs_dir=Path(args.outputs_dir),
    )

    print(f"Trained model bundle successfully saved: {args.output}")
    print(f"Data Source: {bundle['data_source']}")
    print(f"Classes: {bundle['classes']}")
    print("Feature ranges:")
    for c in FEATURES:
        print(f"  {c}: {bundle['training_min'][c]:.4f} .. {bundle['training_max'][c]:.4f}")


if __name__ == "__main__":
    main()
