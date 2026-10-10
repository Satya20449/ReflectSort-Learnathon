# ReflectSort Run Instructions (macOS)

Run commands from the `ReflectSort_Integrated` directory.

## 1. Create and activate an environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install -e ".[dev]"
```

## 2. Run diagnostics

```bash
python3 run_reflectsort.py --check
```

## 3. Run one CLI prediction

```bash
python3 run_reflectsort.py --cli 510 150 900
```

Arguments are sample LDR ADC counts, ambient LDR ADC counts, and optional reference count.

## 4. Classify a CSV file

```bash
python3 run_reflectsort.py --csv application/data/sample_readings.csv
```

## 5. Run software simulation

```bash
python3 run_reflectsort.py --sim 2
```

This uses simulated readings and actuator behavior. It does not control physical hardware.

## 6. Run tests

```bash
python3 -m pytest -q
```

## 7. Optional serial bridge

Install `pyserial` via the requirements and use the port shown by your operating system, for example:

```bash
python3 application/serial_reader.py /dev/ttyACM0 --baud 115200 --timeout 2
```

The bridge expects one UTF-8 NDJSON measurement object per line. Example:

```json
{"type":"measurement","request_id":"REQ-001","sample_LDR":1200,"ambient_LDR":800,"reference_value":900}
```

This serial bridge has been tested with mocked serial input only. Do not treat it as physically validated until tested with the actual firmware and board.
