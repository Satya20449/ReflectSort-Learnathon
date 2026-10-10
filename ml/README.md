# ReflectSort — Machine Learning & Dataset Module (Member 2: Kuldeep Singh)

**Module Owner:** Kuldeep Singh  
**Subsystem:** Machine Learning Pipeline, Dataset Generation & Model Artifacts  
**Course:** Machine Learning – Embedded Systems Design (ML-ESD-TEAM-117)

---

## 1. Responsibilities

- Synthetic training-data generation and preprocessing.
- Training pipeline with grouped specimen-level train/validation split.
- Export of approved scikit-learn model bundle (`shade_model.joblib`).
- Feature definition and input bounds tracking.
- Classification, confusion matrix, and evaluation reports.

---

## 2. Model Architecture & Feature Contract

- **Model Type:** Scikit-Learn `Pipeline` composed of:
  1. `StandardScaler()`
  2. `RandomForestClassifier(n_estimators=150, class_weight='balanced', random_state=117)`
- **Ordered Features:**
  1. `sample_LDR`: 12-bit ADC count of reflected light from specimen $[0, 4095]$.
  2. `ambient_LDR`: 12-bit ADC count of ambient light background $[1, 4095]$.
  3. `reflectance_ratio`: Calculated as $\text{sample\_LDR} / \text{ambient\_LDR}$.
- **Target Output Classes:** `["Dark", "Light", "Medium"]`

---

## 3. Dataset Generation & Retraining

To regenerate the synthetic training dataset:
```bash
python ml/generate_demo_data.py
```
This generates 900 simulated records across 300 specimens with 3 repetitions each in `ml/data/demo_data_simulated.csv`.

To retrain the model artifact:
```bash
python ml/train_model.py --data ml/data/demo_data_simulated.csv
```
This writes the trained bundle to `ml/model/shade_model.joblib` and updates evaluation reports in `ml/outputs/`.

---

## 4. Disclaimer

All training and evaluation datasets in this package are **synthetic/simulated software demonstrations**. Accuracy metrics validate the computational pipeline and do not represent physical optical field performance on real grain specimens.
