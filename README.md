# ReflectSort Integration Review Package — Member 2 (Kuldeep)

This package is a reproducible **software integration/demo** for the Seed/Grain Shade Prototype. It is **not hardware validated**. The included model is trained on explicitly simulated readings.

## 1. Reproduce training

Use Python 3.10+ (same Python environment for training and running). From this folder:

```bat
py -m pip install -r requirements.txt
py generate_demo_data.py
py train_model.py --data data/demo_data_simulated.csv
```

`generate_demo_data.py` uses NumPy RNG seed 117 and creates 100 simulated specimen IDs per class, 3 repeat readings per specimen (900 rows total). It samples an ambient reading in 130..165 ADC counts and synthetic sample/ambient ratios from these bands: Dark 1.45..2.35, Medium 2.65..3.75, Light 4.10..5.65, with small random noise. These bands were invented for exercising the pipeline; they are **not measurements or calibrated physical shade thresholds**. Training splits by `specimen_id` to avoid putting repeat readings of one synthetic specimen in both partitions.

The training script fits `StandardScaler` + `RandomForestClassifier` (`n_estimators=150`, `class_weight='balanced'`, `random_state=117`) inside a scikit-learn Pipeline, saves `shade_model.joblib`, and writes metrics to `outputs/`. Re-run the commands to reproduce the model and results. Metrics only describe this synthetic distribution and must not be reported as real-world accuracy.

## 2. Model interface

- Artifact: `shade_model.joblib` (joblib dictionary with `pipeline`, `features`, `classes`, `training_min`, `training_max`, and metadata).
- Exact ordered features: `sample_LDR`, `ambient_LDR`, `reflectance_ratio` where `reflectance_ratio = sample_LDR / ambient_LDR`.
- The saved pipeline includes `StandardScaler`; do not scale inputs separately.
- Random Forest supports `predict_proba`; the demo uses maximum class probability with a 0.60 minimum-confidence threshold.
- Model labels: `Dark`, `Light`, `Medium`.
- Proposed demo mapping: `Dark -> BIN_A`, `Medium -> BIN_B`, `Light -> BIN_C`; invalid/out-of-range/low-confidence -> `HOLD`. Confirm bin arrangement with the hardware/firmware owner before actuation.
- `reference_value` may be accepted by the demo for interface compatibility but is logged only and is **not a model feature**.

## 3. Actual training feature ranges in the bundled model

These ranges are derived from the synthetic training partition. The app's guard checks every model feature against these bounds:

- `sample_LDR`: 181..941
- `ambient_LDR`: 130..165
- `reflectance_ratio`: 1.3401..5.7423

Do not treat these as approved ADC calibration limits. The separate electrical ADC input limit in the current GUI is 0..4095 and must be confirmed against the actual board configuration.

## 4. Example and safety CSV

`data/test_readings_expected.csv` contains 4 representative in-range cases with expected bin outputs and 4 invalid/out-of-range cases expected to return HOLD. It is a software test fixture, not physical sensor data. Run:

```bat
py shade_demo.py --csv data/test_readings_expected.csv
```

The app prints actual results and appends to `prediction_log.csv`. `expected_output` and `case_type` are for human comparison; they are ignored as model features.

## 5. Run app and tests

```bat
py shade_demo.py
py -m unittest discover -s tests -v
```

## 6. Real sensor collection protocol (required before performance claims)

1. Confirm board model, ADC resolution/reference voltage, sensor divider wiring and whether a higher ADC code means brighter or darker. Never assume direction from the LDR alone.
2. Fix LED current/brightness, sensor distance, optical tunnel, sample orientation and integration time. Record ambient/reference measurements and any lighting/position changes.
3. Use unique `specimen_id` for each physical seed/grain; record multiple `run_id` repeats per specimen. Label shade categories using an agreed, documented reference procedure before measuring; do not label based on model output.
4. Record raw ADC values unchanged. Keep the data dictionary and calibration conditions. Do not merge repeated readings from one specimen across train/test splits.
5. Collect specimens across all agreed classes and multiple sessions/positions. Hold out whole specimens (and ideally a later session) for evaluation. Report per-class precision/recall, macro-F1 and confusion matrix; report unknown/reject behaviour separately.
6. Retrain on real labelled readings, review confusions and threshold policy, then run the official acceptance tests. Do not claim real-world accuracy until this is completed.

## 7. Integration confirmations still required

- **Satyam (software demo):** confirm the app consumes exactly the 3 ordered features above, loads this bundle (not a dummy model), maps labels as agreed, and uses the 0.60 confidence threshold / HOLD policy.
- **Ajitesh (firmware/hardware):** confirm board ADC range and scaling, COM port, serial baud rate, message framing/terminator, command response/timeout, and actual bin mapping. `serial_reader.py` currently documents a proposed newline-terminated comma-separated reading at 115200 baud; this is not confirmed hardware protocol. No physical actuation is performed by this Python package.

## Environment and reports

The bundled artifact was loaded and tested with Python 3.13.5, scikit-learn 1.8.0, NumPy 2.3.5, pandas 2.2.3, joblib 1.5.3, and Matplotlib 3.10.8. `requirements.txt` pins these versions and includes pyserial 3.5 for optional serial-reader use. See `outputs/training_evaluation_report.md` for the concise report and `outputs/sample_predictions.csv` for actual outputs on the provided fixture.

## Honest status

Included automated tests validate software behavior on known simulated inputs. No real seed/grain measurements, physical sensor calibration, STM32 communication, servo motion, or real-world accuracy results are claimed.
