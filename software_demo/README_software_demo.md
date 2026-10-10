# Seed/Grain Shade Prototype - Software Demo (Member 3)

KL University | ML-ESD | Team ML-ESD-TEAM-117 | PROJECT-12-VARIANT-06

A Python app that takes sensor readings (typed, simulated, CSV, or serial from the board),
validates them, asks the ML model for a shade group and shows **BIN_A / BIN_B / BIN_C / HOLD**.
Educational prototype only: shade grouping says nothing about seed quality, freshness or safety.

## Setup (PyCharm)
1. File -> Open this folder, create a virtual environment when asked.
2. In the PyCharm terminal: `pip install -r requirements.txt`
3. Run `shade_demo.py`.

## Files
| File | Purpose |
|---|---|
| shade_demo.py | Main app (GUI, CLI, CSV batch), validation, prediction |
| make_dummy_model.py | Makes a SYNTHETIC test model (testing only, not a result) |
| serial_reader.py | Optional: read live readings from the board over USB serial |
| test_shade_demo.py | Unit tests |
| data/sample_readings.csv | Example inputs, including bad ones |
| prediction_log.csv | Created automatically; every prediction is logged |

## Usage
    python shade_demo.py                        # GUI
    python shade_demo.py --cli 450 500 1800     # single reading
    python shade_demo.py --csv data/sample_readings.csv

## Inputs
sample_ldr, ambient_ldr, reference_value - whole numbers, 0-4095 (12-bit ADC assumed; reference > 0).

## Features given to the model (must match Member 2's training, same order)
[sample_ldr, ambient_ldr, reference_value, sample/reference, sample - ambient]

## Safety behaviour
- Missing / out-of-range / zero-reference input -> HOLD (never reaches the model).
- Model confidence below 0.60 or an unknown label -> HOLD.
- No model file -> transparent threshold fallback (placeholder values, not tuned).
- The microcontroller keeps final authority over any actuator movement.

## Integration status
- [ ] Feature list agreed with Member 2
- [ ] Real shade_model.joblib received and loaded ("ML model" shown in the app)
- [ ] Serial line format agreed with Member 4
- [ ] Screenshots saved in screenshots/

## Limitations
No accuracy is claimed here. Thresholds, ADC range and confidence cutoff are assumptions until the team confirms them.
