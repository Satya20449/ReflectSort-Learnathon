# ReflectSort — Python Software Application (Member 3: Satyam Rai)

**Module Owner:** Satyam Rai  
**Subsystem:** User Interface, Prediction Orchestration, Input Validation & Logging  
**Course:** Machine Learning – Embedded Systems Design (ML-ESD-TEAM-117)

---

## 1. Responsibilities

- Host-side graphical interface (Tkinter GUI) and CLI prediction modes.
- Input validation ensuring all sensor readings fall within the STM32 12-bit ADC range ($[0, 4095]$).
- Integration with Member 2's trained ML model bundle (`shade_model.joblib`).
- Physical sorting bin mapping (`Dark -> BIN_A`, `Medium -> BIN_B`, `Light -> BIN_C`).
- Safety policy execution (`HOLD` for low confidence, out-of-training-range inputs, or invalid sensor counts).
- Execution audit logging to `prediction_log.csv`.
- Optional serial communication bridge for real-time UART reception.

---

## 2. Usage Instructions

### A. Run Interactive GUI
```bash
python application/shade_demo.py
```
- Enter numeric ADC counts for Sample LDR, Ambient LDR, and optional Reference baseline.
- Click **"Classify / Sort"** to obtain real-time sorting action and confidence score.
- Click **"Simulate Sensor Reading"** to populate realistic synthetic readings.
- Click **"Batch CSV..."** to run predictions across a batch file.

### B. Run CLI Single-Reading Prediction
```bash
python application/shade_demo.py --cli 510 150 900
```
Outputs sorting decision, confidence percentage, and explanation note.

### C. Run Batch CSV Prediction
```bash
python application/shade_demo.py --csv application/data/sample_readings.csv
```
Processes rows and appends results to `application/prediction_log.csv`.

### D. System Diagnostics
```bash
python application/shade_demo.py --check
```
Displays loaded model metadata, feature definitions, training boundaries, and confidence threshold.

---

## 3. Disclaimer

This software prototype classifies surface reflectance shade. It does not perform chemical, nutritional, or biological food-safety analysis.
