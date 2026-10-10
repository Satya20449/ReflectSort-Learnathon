# ReflectSort ML Training & Evaluation Report

**Owner:** Kuldeep Singh (Member 2 — ML)  
**Status:** Software/demo verification only; not hardware validated.  
**Training-data source:** SIMULATED. No Kaggle dataset or physical sensor readings were used for this bundled model.

## Model interface

- Artifact: `shade_model.joblib`, a joblib-serialized dictionary containing `pipeline`, `features`, `classes`, `training_min`, `training_max`, and training metadata fields.
- Ordered model inputs (exact): `sample_LDR`, `ambient_LDR`, `reflectance_ratio`.
- Ratio calculation in both training and demo: `reflectance_ratio = sample_LDR / ambient_LDR`. Ambient must be greater than zero. Do not reverse the division and do not add `reference_value` as a feature.
- Pipeline: `StandardScaler` followed by `RandomForestClassifier` with 150 estimators, balanced class weights, and random state 117. Do not scale the inputs externally.
- Class labels: `Dark`, `Light`, `Medium` (classifier class order). Demo mapping: `Dark -> BIN_A`, `Medium -> BIN_B`, `Light -> BIN_C`. This mapping is a software proposal and must be confirmed by the team before any actuator use.
- Confidence policy: maximum `predict_proba` value must be at least 0.60; otherwise `HOLD`. Invalid readings and readings outside the simulated training feature ranges also return `HOLD`.
- Optional `reference_value` is accepted by the current demo for compatibility/logging only; it is not used by the model.

## Training and held-out synthetic evaluation

The generator creates 900 synthetic rows (100 synthetic specimen IDs per class, 3 repeat readings per specimen). The split groups by `specimen_id` (75%/25%) so repeated readings from one generated specimen do not cross partitions. The held-out partition contains 225 rows.

| Metric | Result | Interpretation |
|---|---:|---|
| Accuracy | 1.0000 (100%) | On the synthetic held-out split only |
| Macro-F1 | 1.0000 | On the synthetic held-out split only |
| Held-out rows | 225 | Generated/simulated rows |

These perfect scores reflect the clean, separated synthetic class bands. They do **not** estimate performance on real seeds/grains, real illumination, sensor noise, hardware ADC scaling, or unseen physical samples.

## Demo fixture check

`data/test_readings_expected.csv` was run through the app. All **8/8** expected outcomes matched: four representative in-range synthetic examples mapped to the proposed bins, and four invalid/out-of-range cases returned `HOLD`. This is a deterministic software fixture check, not an independent real-world test set. See `outputs/sample_predictions.csv` for the actual output rows.

Two automated unit tests passed: representative prediction mapping and invalid-input HOLD behavior. The model loaded successfully in the environment listed below.

## Verified software environment

The bundle was loaded and tested with Python **3.13.5**, scikit-learn **1.8.0**, NumPy **2.3.5**, pandas **2.2.3**, joblib **1.5.3**, and Matplotlib **3.10.8**. `requirements.txt` pins these versions and includes pyserial 3.5 for optional serial-reader functionality. Use the same versions for the most reproducible joblib loading. Do not load an untrusted `.joblib` file; joblib/pickle-based artifacts can execute code during deserialization.

## Remaining integration / validation work

Satyam should confirm that his demo loads this exact bundle and preserves the three-feature order, ratio formula, class-to-bin mapping, 0.60 threshold, and `HOLD` behavior. Ajitesh should confirm ADC scale, wiring/sensor polarity, serial framing/baud/port, and actual physical bin mapping. No confirmation from either teammate is implied by this report. Collect independently labelled real sensor readings and evaluate held-out physical specimens/sessions before making any real-world accuracy claim.
