# ReflectSort Test Results

## Environment

- Runtime: Python 3.13.5
- Platform: Linux x86_64 audit container
- pytest: 9.0.2
- These results are from the actual commands executed in this audit environment. A fresh dependency-isolated virtual environment was not created, so clean-environment installation is not claimed.

## Automated tests

Command:

```bash
python3 -m pytest -q
```

Result: **102 passed in 5.59 seconds; 0 failed; 0 collection errors.**

Includes mock-serial NDJSON tests for valid measurements, optional fields, malformed payloads, timeouts, and communication failures.

## Application smoke tests

| Command | Result |
|---|---|
| `python3 run_reflectsort.py --check` | Exit 0; model and subsystem diagnostics completed |
| `python3 run_reflectsort.py --cli 510 150 900` | Exit 0; returned `BIN_B` with reported confidence 100% for this supplied sample |
| `python3 run_reflectsort.py --csv application/data/sample_readings.csv` | Exit 0; processed 10 rows; invalid/out-of-range examples returned `HOLD` |
| `python3 run_reflectsort.py --sim 2` | Exit 0; processed 2 simulated specimens and printed actuator audit trail |

The prediction confidence and outcomes above describe this software's supplied examples only; they are not measured real-world accuracy.

## Not tested

- Fresh isolated virtual-environment installation from scratch.
- Physical STM32 ADC acquisition.
- Physical UART/NDJSON exchange with firmware.
- Physical PWM waveform, servo movement, mechanical sorting, or calibration.
- Accuracy on a real physical grain/seed dataset.
