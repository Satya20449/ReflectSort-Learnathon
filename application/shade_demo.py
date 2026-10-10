"""
ReflectSort — Member 3 (Satyam Rai): Python Software Application
Course: Machine Learning – Embedded Systems Design (ML-ESD)
Team: ML-ESD-TEAM-117 | Project ID: PROJECT-12-VARIANT-06

Accepts sensor readings (interactive GUI, CLI arguments, CSV batch, or serial stream),
validates inputs against hardware ADC limits, queries Member 2's trained ML model,
and displays/logs the resulting sorting action (BIN_A / BIN_B / BIN_C / HOLD).
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import math
import os
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import pandas as pd

# Path resolution: find project root
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# Default model location (Member 2's approved artifact)
DEFAULT_MODEL_PATH = PROJECT_ROOT / "ml" / "model" / "shade_model.joblib"
# Local fallback if model is placed beside application
LOCAL_MODEL_PATH = BASE_DIR / "shade_model.joblib"

LOG_FILE = BASE_DIR / "prediction_log.csv"

# Hardware ADC Limits (12-bit ADC on STM32)
ADC_MIN: int = 0
ADC_MAX: int = 4095
CONF_THRESHOLD: float = 0.60

# Model class to physical bin mapping convention
SHADE_TO_BIN: Dict[str, str] = {
    "Dark": "BIN_A",
    "Medium": "BIN_B",
    "Light": "BIN_C",
}

EXPECTED_FEATURES: List[str] = ["sample_LDR", "ambient_LDR", "reflectance_ratio"]


def resolve_model_path(custom_path: Optional[Path] = None) -> Path:
    """Locate the authoritative shade_model.joblib file."""
    if custom_path and Path(custom_path).exists():
        return Path(custom_path)
    if DEFAULT_MODEL_PATH.exists():
        return DEFAULT_MODEL_PATH
    if LOCAL_MODEL_PATH.exists():
        return LOCAL_MODEL_PATH
    raise FileNotFoundError(
        f"Model bundle not found. Checked:\n  - {DEFAULT_MODEL_PATH}\n  - {LOCAL_MODEL_PATH}"
    )


def validate_input(
    sample: Any,
    ambient: Any,
    reference: Optional[Any] = None,
) -> Tuple[bool, str]:
    """
    Validate raw sensor ADC counts before ML inference.
    Returns (is_valid, explanation).
    """
    if sample is None or ambient is None:
        return False, "Missing sensor value: sample and ambient readings are required."

    try:
        s = float(sample)
        a = float(ambient)
        r = float(reference) if reference not in (None, "") else None
    except (TypeError, ValueError):
        return False, "Sensor readings must be numeric numbers."

    if not math.isfinite(s) or not math.isfinite(a) or (r is not None and not math.isfinite(r)):
        return False, "Sensor readings must be finite numbers (no NaN or Inf)."

    if not (ADC_MIN <= s <= ADC_MAX):
        return False, f"sample_ldr={s:.2f} is outside 12-bit ADC range [{ADC_MIN}, {ADC_MAX}]."

    if not (ADC_MIN <= a <= ADC_MAX):
        return False, f"ambient_ldr={a:.2f} is outside 12-bit ADC range [{ADC_MIN}, {ADC_MAX}]."

    if a <= 0:
        return False, f"ambient_ldr must be > 0 for reflectance ratio calculation (got {a})."

    if r is not None and not (ADC_MIN <= r <= ADC_MAX):
        return False, f"reference_value={r:.2f} is outside 12-bit ADC range [{ADC_MIN}, {ADC_MAX}]."

    return True, "Valid input."


class Predictor:
    """
    Inference engine that loads and executes Member 2's approved ML model bundle.
    """

    def __init__(
        self,
        model_path: Optional[Path] = None,
        confidence_threshold: float = CONF_THRESHOLD,
    ) -> None:
        self.model_path = resolve_model_path(model_path)
        self.confidence_threshold = confidence_threshold
        self._load_model()

    def _load_model(self) -> None:
        try:
            self.bundle = joblib.load(self.model_path)
        except Exception as e:
            raise RuntimeError(f"Failed to load model from {self.model_path}: {e}") from e

        if not isinstance(self.bundle, dict) or "pipeline" not in self.bundle:
            raise ValueError(f"Model at {self.model_path} is not a valid ReflectSort model bundle dictionary.")

        self.pipeline = self.bundle["pipeline"]
        self.features = self.bundle.get("features", EXPECTED_FEATURES)
        self.classes = self.bundle.get("classes", list(SHADE_TO_BIN.keys()))
        self.training_min = self.bundle.get("training_min", {})
        self.training_max = self.bundle.get("training_max", {})
        self.data_source = self.bundle.get("data_source", "UNKNOWN")
        self.source = f"Member 2 Model: {self.model_path.name} (Source: {self.data_source})"

    def predict(
        self,
        sample: Any,
        ambient: Any,
        reference: Optional[Any] = None,
    ) -> Tuple[str, float, str]:
        """
        Predict sorting action for a given sensor reading.

        Returns:
            (action, confidence, explanation)
            where action is one of 'BIN_A', 'BIN_B', 'BIN_C', or 'HOLD'.
        """
        # Step 1: Input Validation Gate
        ok, msg = validate_input(sample, ambient, reference)
        if not ok:
            return "HOLD", 0.0, f"Rejected input: {msg}"

        s = float(sample)
        a = float(ambient)
        ratio = s / a

        values = {
            "sample_LDR": s,
            "ambient_LDR": a,
            "reflectance_ratio": ratio,
        }

        # Step 2: Training Range Guard (Prevent out-of-distribution hallucinations)
        for col in self.features:
            if col in self.training_min and col in self.training_max:
                lo = float(self.training_min[col])
                hi = float(self.training_max[col])
                val = float(values.get(col, 0.0))
                if val < lo or val > hi:
                    return (
                        "HOLD",
                        0.0,
                        f"Feature '{col}'={val:.4f} outside model training range [{lo:.4f}, {hi:.4f}]",
                    )

        # Step 3: ML Inference
        row = pd.DataFrame([[values[f] for f in self.features]], columns=self.features)

        try:
            if hasattr(self.pipeline, "predict_proba"):
                probs = self.pipeline.predict_proba(row)[0]
                classes = list(self.pipeline.named_steps["classifier"].classes_)
                best_idx = int(probs.argmax())
                raw_shade = str(classes[best_idx])
                conf = float(probs[best_idx])
            else:
                raw_shade = str(self.pipeline.predict(row)[0])
                conf = 1.0
        except Exception as e:
            return "HOLD", 0.0, f"Inference execution error: {e}"

        # Step 4: Bin Mapping & Confidence Safety Policy
        bin_action = SHADE_TO_BIN.get(raw_shade)
        if bin_action is None:
            return "HOLD", conf, f"Unrecognized shade class '{raw_shade}' from model"

        if conf < self.confidence_threshold:
            return (
                "HOLD",
                conf,
                f"Low confidence ({conf:.2%}) below threshold {self.confidence_threshold:.2%} (Raw shade: {raw_shade})",
            )

        return bin_action, conf, f"Model classified as '{raw_shade}' -> {bin_action}"


def log_prediction(
    sample: Any,
    ambient: Any,
    reference: Optional[Any],
    decision: str,
    confidence: float,
    note: str,
    log_file: Path = LOG_FILE,
) -> None:
    """Append a prediction event to the CSV log."""
    new_file = not log_file.exists() or log_file.stat().st_size == 0
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["timestamp", "sample_ldr", "ambient_ldr", "reference_value", "decision", "confidence", "note"])
        writer.writerow([
            dt.datetime.now(dt.timezone.utc).isoformat(),
            sample,
            ambient,
            reference if reference not in (None, "") else "",
            decision,
            f"{confidence:.4f}",
            note,
        ])


def simulate_reading() -> Tuple[int, int, int]:
    """Generate a realistic synthetic reading matching Member 2's dataset."""
    ambient = random.randint(130, 165)
    # Pick a random shade band
    shade = random.choice(["Dark", "Medium", "Light"])
    if shade == "Dark":
        ratio = random.uniform(1.45, 2.30)
    elif shade == "Medium":
        ratio = random.uniform(2.70, 3.70)
    else:
        ratio = random.uniform(4.15, 5.60)

    sample = int(round(ambient * ratio + random.normalvariate(0, 4)))
    sample = max(ADC_MIN, min(ADC_MAX, sample))
    reference = random.randint(890, 915)
    return sample, ambient, reference


def run_csv_batch(predictor: Predictor, csv_path: str, log_file: Path = LOG_FILE) -> List[Dict[str, Any]]:
    """Process a batch of sensor readings from a CSV file."""
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Input CSV file not found: {csv_path}")

    results = []
    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row_idx, row in enumerate(reader, start=1):
            s_raw = row.get("sample_ldr") or row.get("sample_LDR")
            a_raw = row.get("ambient_ldr") or row.get("ambient_LDR")
            r_raw = row.get("reference_value") or row.get("reference") or None

            decision, conf, note = predictor.predict(s_raw, a_raw, r_raw)
            log_prediction(s_raw, a_raw, r_raw, decision, conf, note, log_file=log_file)

            res = {
                "row": row_idx,
                "sample_ldr": s_raw,
                "ambient_ldr": a_raw,
                "reference_value": r_raw,
                "decision": decision,
                "confidence": conf,
                "note": note,
            }
            results.append(res)
            print(f"Row {row_idx:3d} | S={str(s_raw):<6} A={str(a_raw):<6} R={str(r_raw or '-'):<6} -> {decision:<8} (conf={conf:.2%}) | {note}")

    print(f"\nProcessed {len(results)} rows. Predictions logged to: {log_file}")
    return results


def run_gui(predictor: Predictor) -> None:
    """Launch the interactive Tkinter graphical demo."""
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title("ReflectSort — Seed/Grain Optical Shade Sorting Demo")
    root.geometry("620x580")
    root.resizable(True, True)

    bin_colors = {
        "BIN_A": "#d7ccc8",  # Brown/Dark
        "BIN_B": "#ffe0b2",  # Amber/Medium
        "BIN_C": "#fff9c4",  # Yellow/Light
        "HOLD": "#ffcdd2",   # Red/Hold
    }

    vars_dict = {
        "sample": tk.StringVar(value="510"),
        "ambient": tk.StringVar(value="150"),
        "reference": tk.StringVar(value="900"),
    }

    # Header
    ttk.Label(root, text="ReflectSort — Explainable Optical Mini-Sorting Cell", font=("Arial", 14, "bold")).pack(pady=(10, 2))
    ttk.Label(root, text=f"Active ML Model: {predictor.model_path.name} | Data Source: {predictor.data_source}", font=("Arial", 9, "italic")).pack()
    ttk.Label(root, text="Features: sample_LDR, ambient_LDR, reflectance_ratio (= sample / ambient)", font=("Arial", 9)).pack(pady=2)

    # Input Frame
    input_frame = ttk.LabelFrame(root, text=" Optical Sensor Inputs (12-bit ADC: 0 - 4095) ", padding=10)
    input_frame.pack(padx=15, pady=8, fill="x")

    for key, label_text, default_val in [
        ("sample", "Sample LDR Reading (counts):", "510"),
        ("ambient", "Ambient LDR Reading (counts):", "150"),
        ("reference", "Reference Calibration (optional):", "900"),
    ]:
        row = ttk.Frame(input_frame)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text=label_text, width=32).pack(side="left")
        ttk.Entry(row, textvariable=vars_dict[key], width=16).pack(side="left")

    # Decision Banner
    result_box = tk.Label(
        root,
        text="READY",
        font=("Arial", 22, "bold"),
        width=16,
        height=2,
        bg="#eeeeee",
        relief="groove",
    )
    result_box.pack(pady=10)

    detail_label = ttk.Label(root, text="Enter sensor values and click 'Classify / Sort'", font=("Arial", 9), wraplength=580, justify="center")
    detail_label.pack(pady=2)

    # Prediction History Listbox
    history_frame = ttk.LabelFrame(root, text=" Sorting Action History ", padding=5)
    history_frame.pack(padx=15, pady=5, fill="both", expand=True)

    history_list = tk.Listbox(history_frame, height=6, font=("Courier", 9))
    history_list.pack(side="left", fill="both", expand=True)
    scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=history_list.yview)
    scrollbar.pack(side="right", fill="y")
    history_list.config(yscrollcommand=scrollbar.set)

    def execute_prediction(s_val, a_val, r_val):
        decision, conf, note = predictor.predict(s_val, a_val, r_val)
        result_box.config(text=decision, bg=bin_colors.get(decision, "#eeeeee"))
        detail_label.config(text=f"Decision: {decision} | Confidence: {conf:.2%}\n{note}")
        time_str = dt.datetime.now().strftime("%H:%M:%S")
        history_list.insert(0, f"[{time_str}] S={s_val} A={a_val} R={r_val or '-'} -> {decision} ({conf:.1%})")
        log_prediction(s_val, a_val, r_val, decision, conf, note)

    def on_predict_click():
        s = vars_dict["sample"].get().strip()
        a = vars_dict["ambient"].get().strip()
        r = vars_dict["reference"].get().strip()
        execute_prediction(s, a, r if r else None)

    def on_simulate_click():
        s, a, r = simulate_reading()
        vars_dict["sample"].set(str(s))
        vars_dict["ambient"].set(str(a))
        vars_dict["reference"].set(str(r))
        execute_prediction(s, a, r)

    def on_csv_click():
        file_path = filedialog.askopenfilename(
            title="Select Sensor Readings CSV",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
        )
        if file_path:
            try:
                run_csv_batch(predictor, file_path)
                messagebox.showinfo("Batch Complete", f"Batch completed. Log appended to:\n{LOG_FILE.name}")
            except Exception as e:
                messagebox.showerror("CSV Error", str(e))

    # Action Buttons
    button_bar = ttk.Frame(root)
    button_bar.pack(pady=10)
    ttk.Button(button_bar, text="Classify / Sort", command=on_predict_click).pack(side="left", padx=5)
    ttk.Button(button_bar, text="Simulate Sensor Reading", command=on_simulate_click).pack(side="left", padx=5)
    ttk.Button(button_bar, text="Batch CSV...", command=on_csv_click).pack(side="left", padx=5)

    ttk.Label(
        root,
        text="DISCLAIMER: Shade prototype software only. Not a food safety or grain purity analyzer.",
        font=("Arial", 8, "italic"),
        foreground="#666666",
    ).pack(pady=(0, 8))

    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="ReflectSort — Seed/Grain Optical Shade Sorting Demo")
    parser.add_argument("--cli", nargs="+", type=float, metavar="VAL", help="Direct sensor input: SAMPLE AMBIENT [REFERENCE]")
    parser.add_argument("--csv", type=str, metavar="PATH", help="Path to batch CSV file containing sample_ldr, ambient_ldr")
    parser.add_argument("--check", action="store_true", help="Run model and environment diagnostic checks")
    parser.add_argument("--model", type=str, help="Custom path to shade_model.joblib")
    args = parser.parse_args()

    model_path = Path(args.model) if args.model else None
    predictor = Predictor(model_path=model_path)

    if args.check:
        print("=" * 60)
        print("  ReflectSort Diagnostic Check")
        print("=" * 60)
        print(f"Model Path:         {predictor.model_path}")
        print(f"Data Source:        {predictor.data_source}")
        print(f"Expected Features:  {predictor.features}")
        print(f"Output Classes:     {predictor.classes}")
        print(f"Confidence Limit:   {predictor.confidence_threshold:.2%}")
        print(f"Training Ranges:")
        for k in predictor.features:
            print(f"  - {k}: {predictor.training_min.get(k)} to {predictor.training_max.get(k)}")
        print("=" * 60)
        print("Diagnostics completed successfully.")
    elif args.cli is not None:
        if len(args.cli) not in (2, 3):
            parser.error("--cli requires 2 or 3 numbers: SAMPLE_LDR AMBIENT_LDR [REFERENCE_VALUE]")
        sample = args.cli[0]
        ambient = args.cli[1]
        ref = args.cli[2] if len(args.cli) == 3 else None
        decision, conf, note = predictor.predict(sample, ambient, ref)
        log_prediction(sample, ambient, ref, decision, conf, note)
        print(f"Decision:    {decision}")
        print(f"Confidence:  {conf:.2%}")
        print(f"Explanation: {note}")
    elif args.csv:
        run_csv_batch(predictor, args.csv)
    else:
        run_gui(predictor)


if __name__ == "__main__":
    main()
