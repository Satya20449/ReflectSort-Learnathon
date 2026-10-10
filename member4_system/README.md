# ReflectSort — Member 4 Subsystem: System Architecture, Simulation & Validation

**Project:** ReflectSort — Sensor-Based Seed/Grain Shade Classification and Sorting Prototype  
**Course:** Machine Learning – Embedded Systems Design (ML–ESD)  
**Project Variant:** PROJECT-12-VARIANT-06 | **Team:** ML-ESD-TEAM-117  
**Author:** Ajitesh Karan (2500032236) — Member 4  
**Selected Microcontroller:** STMicroelectronics STM32 NUCLEO-F446RE  

---

## 1. Subsystem Overview & Responsibilities

This repository contains the standalone **Member 4** deliverable for the ReflectSort prototype. It implements the hardware-side data schemas, optical sensor simulator, embedded decision validator, mechanical actuator simulator, hardware planning, STM32 firmware architecture, and automated test suite.

### Team Division of Ownership:
- **Satya Nayak (2500030899):** Team Lead, repository coordination, end-to-end integration.
- **Kuldeep Singh (2500031372):** Labeled dataset, ML training pipeline, classification model evaluation.
- **Satyam Rai (2500032600):** Main Python application, GUI/CLI dashboard, serial manager.
- **Ajitesh Karan (2500032236 — Me):** System architecture, hardware plan, sensor/actuator simulation, decision validation safety gate, firmware design, automated testing.

> [!NOTE]
> **Hardware Status:** All modules in this package currently execute in pure Python software simulation. No physical STM32 board, LDR sensors, or servo motors are connected. All simulated records are strictly labeled `data_source="simulated"`.

---

## 2. Directory Structure

```
member4_system/
├── README.md                     # Comprehensive project documentation & usage guide
├── requirements.txt              # Minimal project dependencies (pytest)
├── pyproject.toml                # Package metadata and build configuration
├── pytest.ini                    # Test runner configuration & pythonpath settings
├── .gitignore                    # Python, virtualenv & IDE ignore rules
├── interface_spec.md             # Inter-module data contracts across all 4 team members
├── hardware_plan.md              # STM32 NUCLEO-F446RE circuit schematics, BOM & pinouts
├── firmware_design.md            # 10-stage STM32 firmware pipeline, state machine & HAL C-code
├── test_plan.md                  # Complete verification matrix (46 automated + 5 hardware tests)
├── system_architecture.mmd       # Mermaid diagram showing end-to-end flow & team ownership
├── src/
│   └── reflectsort_member4/
│       ├── __init__.py           # Package exports & versioning
│       ├── schemas.py            # Data models (SensorRecord, DecisionRequest, DecisionResponse, ActuatorEvent)
│       ├── sensor_simulator.py   # Optical sensing simulator with seedable noise & demo fixtures
│       ├── decision_validator.py # Hardware safety validator enforcing timeouts, IDs, replay protection & labels
│       └── actuator_simulator.py # Diverter gate simulator enforcing angle limits, pulse widths & state safety
├── examples/
│   └── run_simulation.py         # End-to-end interactive demonstration script (7 scenarios)
├── tests/
│   ├── __init__.py
│   ├── test_schemas.py           # Unit tests for data types, bounds, NaN rejection, zero-division & JSON-lines
│   ├── test_sensor_simulator.py  # Unit tests for reproducibility, seed control & demo fixtures
│   ├── test_decision_validator.py# Unit tests for timeouts, boundary checks, replay protection & gating
│   ├── test_actuator_simulator.py# Unit & integration tests for diverter motion, pulse widths & full pipeline
│   └── test_simulation_regression.py # Regression tests for standalone demo execution & scenario logic
└── results/
    └── test_results.txt          # Real execution log from pytest (46 passed)
```

---

## 3. Quick Start & Setup Instructions (macOS / Linux)

### 3.1 Prerequisites
- Python 3.10+ (Tested with Python 3.14 on macOS)
- Standard Unix terminal (`zsh` or `bash`)

### 3.2 Virtual Environment & Dependency Installation

Navigate to the `member4_system` directory:

```bash
cd member4_system

# 1. Create a clean virtual environment
python3 -m venv .venv

# 2. Activate the virtual environment
source .venv/bin/activate

# 3. Install required testing dependencies
pip install -r requirements.txt
```

---

## 4. Running the Interactive Simulation

Run the end-to-end demonstration script which walks through 7 real-world scenarios (including normal classification, foreign matter rejection, host timeout, corrupted request IDs, and unpermitted labels):

```bash
# Ensure src directory is on PYTHONPATH
PYTHONPATH=src python3 examples/run_simulation.py
```

### Example Demonstration Output:
```text
================================================================================
  REFLECTSORT — SENSOR-BASED GRAIN SHADE SORTING PROTOTYPE
  Member 4: System Architecture, Simulation & Validation Subsystem
  Author: Ajitesh Karan (2500032236) | Team: ML-ESD-TEAM-117
================================================================================
  [NOTICE] Pure software simulation running on macOS / Python 3.
  No physical STM32 NUCLEO-F446RE, LDR sensors, or servo hardware connected.
================================================================================

--- [Scenario 1]: Light Shade Grain Sample (Nominal High Reflectance) ---
  [Sensor Acquisition] Specimen: GRAIN-001 | Profile Fixture: LIGHT_GRAIN
    - Sample LDR:         3205.92 counts (12-bit, 0-4095) -> 2.583 V
    - Ambient LDR:         851.40 counts (12-bit, 0-4095) -> 0.686 V
    - Reference Baseline: 2404.36 counts (12-bit, 0-4095) -> 1.937 V
    - Differential LDR:   2354.52 counts
    - Contrast Ratio:      0.9793
    - Data Source Flag:   'simulated'

  [Host ML Decision Input] (Supplied demonstration decision):
    - Proposed Label:     BIN_A
    - Confidence Score:   96.00%
    - Response Request ID:REQ-GRAIN-001 (Expected: REQ-GRAIN-001)
    - Simulated Latency:  0.120 s (Standard Timeout Limit: 2.0 s)

  [Decision Validator Gate]:
    - Validated Status:   PASSED (Valid)
    - Action Permitted:   BIN_A
    - Validation Reason:  Decision 'BIN_A' successfully verified and permitted

  [Actuator Simulator Execution]:
    - Event ID:           ACT-EVT-00001
    - Actuator State:     DIVERT_BIN_A
    - Diverter Angle:     45.0°
    - PWM Pulse Width:    1.250 ms (50 Hz PWM)
    - Execution Status:   EXECUTED
    - Event Reason:       Diverter successfully actuated to 45.0° for BIN_A
```

---

## 5. Running Automated Tests

Run the complete 46-test automated verification suite:

```bash
pytest -v
```

To run with short tracebacks or generate a new test report:
```bash
PYTHONPATH=src pytest -v --tb=short > results/test_results.txt
```

---

## 6. How Teammates Integrate This Module

The `reflectsort_member4` package is fully modular and self-contained.

### 6.1 Integration with Satyam Rai (Main Application)

Satyam's UI / serial orchestration layer can import schemas and the validator directly:

```python
from reflectsort_member4 import DecisionValidator, DecisionResponse, SortingDecision

# Initialize safety validator (standard 2.0s timeout)
validator = DecisionValidator()

# Incoming raw JSON string received from serial or WebSocket
raw_json_dict = serial_manager.read_json_line()

# Validate before commanding any physical or simulated movement
val_result = validator.validate(
    response=raw_json_dict,
    expected_request_id=active_specimen_request_id,
    request_timestamp=specimen_dispatched_timestamp,
)

if val_result.is_valid:
    print(f"Action permitted: {val_result.validated_action.value}")
    # Forward validated action to servo controller
else:
    print(f"Safety Gate Blocked Movement: {val_result.reason} ({val_result.error_code})")
    # Command safe HOLD
```

### 6.2 Integration with Kuldeep Singh (ML Model Pipeline)

Kuldeep can extract numerical features from sensor records without dealing with raw framing:

```python
from reflectsort_member4 import SensorRecord

# Parse sensor record
record = SensorRecord.from_dict(incoming_payload)

# Extract formatted feature dictionary
features = record.to_model_features()
# features == {
#   'sample_LDR': 3200.0,
#   'ambient_LDR': 850.0,
#   'reference_value': 2400.0,
#   'differential_LDR': 2350.0,
#   'contrast_ratio': 0.9791,
#   'ambient_ratio': 3.7647
# }

# Pass to model for inference
predicted_label, confidence = my_trained_classifier.predict(features)
```

---

## 7. Current Limitations & Pending Physical Checks

### Current Software Limitations:
1. Optical measurements are generated via synthetic statistical distributions (`DEMO_FIXTURE_PROFILES`) and do not represent empirical physical grain measurements.
2. Latency timing is simulated using local timestamps rather than physical UART baud transmission delays.

### Pending Physical Hardware Verification:
- **HW-ELEC-01:** DMM voltage clamping check ($V_{\text{ADC}} \le 3.30\,\text{V}$).
- **HW-ELEC-02:** Servo power rail isolation (preventing MCU brownouts under motor stall).
- **HW-PWM-01:** Oscilloscope verification of TIM3 PWM pulse widths ($1.0\,\text{ms} - 2.0\,\text{ms}$).
- **HW-OPT-01:** Optical chamber stray ambient light attenuation measurement.
- **HW-COMM-01:** 115200 baud UART packet integrity stress test over ST-LINK VCP.
