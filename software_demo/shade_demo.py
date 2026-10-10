"""
Seed/Grain Shade Prototype - Member 3: Python Software Demo
-----------------------------------------------------------
Accepts sensor readings (typed, simulated, or from a CSV), validates them,
asks Member 2's model for a prediction, and shows BIN_A / BIN_B / BIN_C / HOLD.

Run GUI :  python shade_demo.py
Run CLI :  python shade_demo.py --cli 1800 600 1750
Run CSV :  python shade_demo.py --csv readings.csv   (columns: sample_ldr,ambient_ldr,reference_value)
"""
import argparse, csv, os, random, sys, datetime

MODEL_FILE = "shade_model.joblib"        # Member 2 saves the trained model here
ADC_MIN, ADC_MAX = 0, 4095               # 12-bit ADC range (adjust if Member 4 uses 16-bit)
CONF_THRESHOLD = 0.60                    # below this confidence -> HOLD
LABELS = ("BIN_A", "BIN_B", "BIN_C", "HOLD")

# ---------- 1. validation (mirrors the 'MCU keeps final authority' rule) ----------
def validate(sample, ambient, reference):
    """Return (ok, message). Bad input must never reach the model."""
    for name, v in (("sample_ldr", sample), ("ambient_ldr", ambient), ("reference_value", reference)):
        if v is None:
            return False, f"{name} is missing"
        if not (ADC_MIN <= v <= ADC_MAX):
            return False, f"{name}={v} is outside {ADC_MIN}-{ADC_MAX}"
    if reference <= 0:
        return False, "reference_value must be > 0"
    return True, "ok"

# ---------- 2. features (must match Member 2's training features!) ----------
def make_features(sample, ambient, reference):
    ratio = sample / reference                 # reflectance-like value
    corrected = sample - ambient               # ambient-corrected signal
    return [sample, ambient, reference, ratio, corrected]

# ---------- 3. model loading with a fallback ----------
class Predictor:
    def __init__(self):
        self.model, self.source = None, "FALLBACK threshold rule (no model file found)"
        if os.path.exists(MODEL_FILE):
            try:
                import joblib
                self.model = joblib.load(MODEL_FILE)
                self.source = f"ML model: {MODEL_FILE}"
            except Exception as e:
                self.source = f"FALLBACK rule (model failed to load: {e})"

    def predict(self, sample, ambient, reference):
        ok, msg = validate(sample, ambient, reference)
        if not ok:
            return "HOLD", 0.0, f"Rejected input: {msg}"
        x = make_features(sample, ambient, reference)
        if self.model is not None:
            if hasattr(self.model, "predict_proba"):
                probs = self.model.predict_proba([x])[0]
                i = int(probs.argmax())
                label, conf = str(self.model.classes_[i]), float(probs[i])
            else:
                label, conf = str(self.model.predict([x])[0]), 1.0
            if label not in LABELS or conf < CONF_THRESHOLD:
                return "HOLD", conf, f"Low confidence / unknown label ({label}, {conf:.2f})"
            return label, conf, "model prediction"
        # fallback: simple transparent thresholds on the ratio (placeholder until model is ready)
        ratio = x[3]
        if ratio < 0.4:   return "BIN_A", 0.9, "ratio < 0.4 (dark)"
        if ratio < 0.8:   return "BIN_B", 0.9, "0.4 <= ratio < 0.8 (medium)"
        if ratio <= 1.3:  return "BIN_C", 0.9, "0.8 <= ratio <= 1.3 (light)"
        return "HOLD", 0.0, "ratio out of expected range"

# ---------- 4. simulator ----------
def simulate():
    """Fake a reading so the demo works without hardware."""
    ref = random.randint(1700, 1900)
    ambient = random.randint(300, 700)
    sample = int(ref * random.choice([0.25, 0.6, 1.0]) + random.randint(-80, 80))
    return max(sample, 0), ambient, ref

LOG_FILE = "prediction_log.csv"
def log_row(s, a, r, label, conf, note):
    new = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        w = csv.writer(f)
        if new: w.writerow(["time", "sample_ldr", "ambient_ldr", "reference", "prediction", "confidence", "note"])
        w.writerow([datetime.datetime.now().isoformat(timespec="seconds"), s, a, r, label, f"{conf:.2f}", note])

# ---------- 5. GUI ----------
def run_gui(pred):
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    root = tk.Tk(); root.title("Seed/Grain Shade Prototype - Demo"); root.geometry("460x470")
    colors = {"BIN_A": "#8d6e63", "BIN_B": "#ffb74d", "BIN_C": "#fff176", "HOLD": "#e57373"}
    vars_ = {k: tk.StringVar() for k in ("sample", "ambient", "reference")}
    ttk.Label(root, text="Enter sensor readings (ADC counts)", font=("Arial", 13, "bold")).pack(pady=8)
    for key, text in (("sample", "Sample LDR"), ("ambient", "Ambient LDR"), ("reference", "Reference value")):
        row = ttk.Frame(root); row.pack(pady=3)
        ttk.Label(row, text=text, width=16).pack(side="left"); ttk.Entry(row, textvariable=vars_[key], width=12).pack(side="left")
    result = tk.Label(root, text="---", font=("Arial", 28, "bold"), width=12, height=2, bg="#eeeeee"); result.pack(pady=12)
    info = ttk.Label(root, text=f"Source: {pred.source}", wraplength=420); info.pack()
    hist = tk.Listbox(root, height=7, width=62); hist.pack(pady=8)

    def show(s, a, r):
        label, conf, note = pred.predict(s, a, r)
        result.config(text=label, bg=colors.get(label, "#eeeeee"))
        info.config(text=f"Confidence {conf:.2f} | {note}\nSource: {pred.source}")
        hist.insert(0, f"{datetime.datetime.now():%H:%M:%S}  S={s} A={a} R={r} -> {label} ({conf:.2f})")
        log_row(s, a, r, label, conf, note)

    def predict_clicked():
        try: s, a, r = (int(vars_[k].get()) for k in ("sample", "ambient", "reference"))
        except ValueError: messagebox.showerror("Input error", "Enter whole numbers in all three fields."); return
        show(s, a, r)

    def sim_clicked():
        s, a, r = simulate()
        for k, v in zip(("sample", "ambient", "reference"), (s, a, r)): vars_[k].set(v)
        show(s, a, r)

    def csv_clicked():
        p = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if p: run_csv(pred, p); messagebox.showinfo("Done", "Batch finished. See prediction_log.csv")

    bar = ttk.Frame(root); bar.pack()
    ttk.Button(bar, text="Predict", command=predict_clicked).pack(side="left", padx=4)
    ttk.Button(bar, text="Simulate sensor", command=sim_clicked).pack(side="left", padx=4)
    ttk.Button(bar, text="Load CSV", command=csv_clicked).pack(side="left", padx=4)
    root.mainloop()

# ---------- 6. CSV / CLI ----------
def run_csv(pred, path):
    with open(path) as f:
        for row in csv.DictReader(f):
            s, a, r = int(row["sample_ldr"]), int(row["ambient_ldr"]), int(row["reference_value"])
            label, conf, note = pred.predict(s, a, r)
            log_row(s, a, r, label, conf, note)
            print(f"S={s} A={a} R={r} -> {label} ({conf:.2f}) {note}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cli", nargs=3, type=int, metavar=("SAMPLE", "AMBIENT", "REF"))
    ap.add_argument("--csv")
    args = ap.parse_args(); p = Predictor()
    if args.cli:
        print(p.predict(*args.cli), "|", p.source)
    elif args.csv:
        run_csv(p, args.csv)
    else:
        run_gui(p)
