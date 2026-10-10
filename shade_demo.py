"""ReflectSort integrated demo: Member 2's real saved model bundle + Member 3 UI.

The bundled model expects exactly these features, in order:
    sample_LDR, ambient_LDR, reflectance_ratio (= sample_LDR / ambient_LDR)
It predicts shade labels Dark/Medium/Light. This app maps those to bin commands.
The optional third reference reading is accepted for compatibility with the demo UI/log,
but is NOT used by this trained model. Confirm the sensor protocol with the team.
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import os
import random
from pathlib import Path

import joblib
import pandas as pd

BASE = Path(__file__).resolve().parent
MODEL_FILE = BASE / "shade_model.joblib"
LOG_FILE = BASE / "prediction_log.csv"
ADC_MIN, ADC_MAX = 0, 4095
CONF_THRESHOLD = 0.60
SHADE_TO_BIN = {"Dark": "BIN_A", "Medium": "BIN_B", "Light": "BIN_C"}

class Predictor:
    def __init__(self, model_path: Path = MODEL_FILE, confidence_threshold: float = CONF_THRESHOLD):
        if not model_path.exists():
            raise FileNotFoundError(f"Model bundle not found: {model_path}. Keep shade_model.joblib beside shade_demo.py.")
        self.bundle = joblib.load(model_path)
        required = ["sample_LDR", "ambient_LDR", "reflectance_ratio"]
        if self.bundle.get("features") != required:
            raise ValueError(f"Unexpected model features {self.bundle.get('features')}; expected {required}.")
        if "pipeline" not in self.bundle:
            raise ValueError("shade_model.joblib is not Member 2's expected model bundle (missing 'pipeline').")
        self.pipeline = self.bundle["pipeline"]
        self.features = required
        self.confidence_threshold = confidence_threshold
        self.source = f"Member 2 model: {model_path.name}"

    def predict(self, sample, ambient, reference=None):
        """Return (BIN_A/BIN_B/BIN_C/HOLD, confidence, explanation).

        reference is accepted for the existing Member 3 three-reading interface, but
        intentionally not used because the trained model's ratio is sample / ambient.
        """
        try:
            sample, ambient = float(sample), float(ambient)
            if reference not in (None, ""):
                reference = float(reference)
        except (TypeError, ValueError):
            return "HOLD", 0.0, "Sensor values must be numeric"
        for name, value in (("sample_ldr", sample), ("ambient_ldr", ambient)):
            if not value.is_integer() or not (ADC_MIN <= value <= ADC_MAX):
                return "HOLD", 0.0, f"{name} must be an integer in {ADC_MIN}..{ADC_MAX}"
        if ambient <= 0:
            return "HOLD", 0.0, "ambient_ldr must be greater than zero"
        if reference is not None and (not reference.is_integer() or not (ADC_MIN <= reference <= ADC_MAX)):
            return "HOLD", 0.0, f"reference_value must be an integer in {ADC_MIN}..{ADC_MAX}"

        ratio = sample / ambient
        row = pd.DataFrame([[sample, ambient, ratio]], columns=self.features)
        for col in self.features:
            lo = float(self.bundle["training_min"][col])
            hi = float(self.bundle["training_max"][col])
            val = float(row.iloc[0][col])
            if val < lo or val > hi:
                return "HOLD", 0.0, f"{col}={val:.4f} outside model's simulated training range [{lo:.4f}, {hi:.4f}]"
        try:
            probs = self.pipeline.predict_proba(row)[0]
            classifier = self.pipeline.named_steps.get("classifier")
            classes = list(classifier.classes_)
            i = int(probs.argmax())
            shade, confidence = str(classes[i]), float(probs[i])
        except (AttributeError, KeyError, ValueError):
            shade = str(self.pipeline.predict(row)[0])
            confidence = 1.0
        if shade not in SHADE_TO_BIN:
            return "HOLD", confidence, f"Unknown shade label from model: {shade}"
        if confidence < self.confidence_threshold:
            return "HOLD", confidence, f"Low confidence ({confidence:.2f} < {self.confidence_threshold:.2f}); predicted shade was {shade}"
        return SHADE_TO_BIN[shade], confidence, f"shade={shade}; sample/ambient={ratio:.4f}. SIMULATED-data model; validate on real readings"


def simulate():
    """Generate an in-range software-demo reading only; not a physical sensor reading."""
    ambient = random.randint(130, 165)
    ratio = random.choice([1.7, 3.4, 5.4])
    sample = int(ambient * ratio)
    reference = random.randint(130, 165)
    return sample, ambient, reference


def log_row(sample, ambient, reference, label, confidence, note):
    new = not LOG_FILE.exists()
    with LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time", "sample_ldr", "ambient_ldr", "reference_value", "prediction", "confidence", "note"])
        w.writerow([dt.datetime.now().isoformat(timespec="seconds"), sample, ambient, reference, label, f"{confidence:.3f}", note])


def run_csv(pred, path):
    count = 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = {x.lower().strip() for x in (reader.fieldnames or [])}
        if "sample_ldr" not in fields or "ambient_ldr" not in fields:
            raise ValueError("CSV must include sample_ldr and ambient_ldr columns. reference_value is optional and is not used by the current model.")
        for row in reader:
            # DictReader keys are case-sensitive; normalize them.
            row = {str(k).lower().strip(): v for k, v in row.items() if k is not None}
            ref = row.get("reference_value", "")
            label, conf, note = pred.predict(row.get("sample_ldr"), row.get("ambient_ldr"), ref or None)
            log_row(row.get("sample_ldr"), row.get("ambient_ldr"), ref, label, conf, note)
            print(f"sample={row.get('sample_ldr')} ambient={row.get('ambient_ldr')} -> {label} (confidence={conf:.2f}) | {note}")
            count += 1
    print(f"Processed {count} rows. Log: {LOG_FILE}")


def run_gui(pred):
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    root = tk.Tk()
    root.title("ReflectSort — Connected ML Demo")
    root.geometry("600x560")
    colors = {"BIN_A": "#d7ccc8", "BIN_B": "#ffe0b2", "BIN_C": "#fff9c4", "HOLD": "#ffcdd2"}
    values = {k: tk.StringVar() for k in ("sample", "ambient", "reference")}
    ttk.Label(root, text="ReflectSort — Seed/Grain Shade Prototype", font=("Arial", 15, "bold")).pack(pady=(12, 4))
    ttk.Label(root, text="Connected to Member 2's shade_model.joblib", font=("Arial", 10)).pack()
    ttk.Label(root, text="Model features: sample_LDR, ambient_LDR, sample_LDR / ambient_LDR", wraplength=550).pack(pady=5)
    ttk.Label(root, text="Reference input is logged for compatibility but is not used by this model.", wraplength=550).pack()
    for key, label, default in (("sample", "Sample LDR", "510"), ("ambient", "Ambient LDR", "150"), ("reference", "Reference (optional)", "150")):
        values[key].set(default)
        row = ttk.Frame(root); row.pack(pady=5)
        ttk.Label(row, text=label, width=22).pack(side="left")
        ttk.Entry(row, textvariable=values[key], width=18).pack(side="left")
    result = tk.Label(root, text="READY", font=("Arial", 24, "bold"), width=18, height=2, bg="#eeeeee")
    result.pack(pady=12)
    details = ttk.Label(root, text=pred.source, wraplength=560, justify="center")
    details.pack(pady=4)
    history = tk.Listbox(root, height=8, width=84)
    history.pack(padx=8, pady=8, fill="x")

    def show(sample, ambient, reference):
        label, conf, note = pred.predict(sample, ambient, reference)
        result.config(text=label, bg=colors.get(label, "#eeeeee"))
        details.config(text=f"Confidence: {conf:.2f}\n{note}\n{pred.source}")
        history.insert(0, f"{dt.datetime.now():%H:%M:%S} S={sample} A={ambient} R={reference or '-'} -> {label} ({conf:.2f})")
        log_row(sample, ambient, reference, label, conf, note)

    def predict_clicked():
        try:
            s = float(values["sample"].get()); a = float(values["ambient"].get())
            r = values["reference"].get().strip()
            show(s, a, r if r else None)
        except ValueError:
            messagebox.showerror("Input error", "Enter numeric sensor readings.")

    def sim_clicked():
        s, a, r = simulate()
        values["sample"].set(str(s)); values["ambient"].set(str(a)); values["reference"].set(str(r))
        show(s, a, r)

    def csv_clicked():
        p = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if p:
            try:
                run_csv(pred, p)
                messagebox.showinfo("CSV complete", f"Processed CSV. See {LOG_FILE.name} beside the app.")
            except Exception as e:
                messagebox.showerror("CSV error", str(e))

    bar = ttk.Frame(root); bar.pack(pady=5)
    ttk.Button(bar, text="Predict", command=predict_clicked).pack(side="left", padx=5)
    ttk.Button(bar, text="Simulate reading", command=sim_clicked).pack(side="left", padx=5)
    ttk.Button(bar, text="Load CSV", command=csv_clicked).pack(side="left", padx=5)
    ttk.Label(root, text="Educational demo only. Model trained on simulated data; confirm bin mapping before hardware use.", wraplength=560).pack(pady=8)
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="ReflectSort connected demo")
    parser.add_argument("--cli", nargs="+", type=float, metavar="VALUE", help="SAMPLE AMBIENT [REFERENCE]")
    parser.add_argument("--csv", help="CSV with sample_ldr and ambient_ldr; optional reference_value")
    args = parser.parse_args()
    pred = Predictor()
    if args.csv:
        run_csv(pred, args.csv)
    elif args.cli is not None:
        if len(args.cli) not in (2, 3):
            parser.error("--cli requires SAMPLE AMBIENT [REFERENCE]")
        print("Model:", pred.source)
        print("Result:", pred.predict(*args.cli))
    else:
        run_gui(pred)

if __name__ == "__main__":
    main()
