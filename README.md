# ReflectSort — Explainable Optical Mini-Sorting Cell

**Project ID:** `PROJECT-12-VARIANT-06`  
**Course:** Machine Learning – Embedded Systems Design (ML-ESD)  
**Team:** `ML-ESD-TEAM-117`  
**Status:** Integrated Software-First Prototype (Phase 1 Complete)

---

## 1. Project Objective & Disclaimer

ReflectSort is a software-first optical mini-sorting cell prototype designed to classify grain and seed surface reflectance shades using photodiode/LDR sensor inputs and a trained machine learning model. The software pipeline validates sensor inputs against microcontroller ADC limits, performs shade classification, verifies decisions against a multi-rule safety gate, and simulates the physical sorting actuation of a multi-bin diverter mechanism.

> [!IMPORTANT]
> **Prototype Classification Disclaimer:**  
> This prototype is strictly an optical surface reflectance shade classifier. It does **not** evaluate grain purity, food safety, biological contamination, moisture, seed viability, or nutritional content.

---

## 2. Team Ownership & Subsystem Architecture

The integrated repository preserves clear separation of ownership across all team members:

| Team Member | Role & Ownership | Subsystem Directory | Core Deliverables |
|---|---|---|---|
| **Kuldeep Singh** | Member 2 — ML & Dataset | [`ml/`](ml) | Synthetic dataset generator, training pipeline (`train_model.py`), approved model bundle (`shade_model.joblib`), evaluation reports. |
| **Satyam Rai** | Member 3 — Python Application | [`application/`](application) | Tkinter GUI, CLI runner, ADC input validation, batch CSV classifier, serial bridge, prediction audit logger. |
| **Ajitesh Karan** | Member 4 — Architecture, Sim & Gate | [`member4_system/`](member4_system) | System architecture, sensor simulation, 8-rule decision safety gate, diverter actuator physics model, test suite. |
| **Satya Nayak** | Team Lead — Integration & Delivery | [`reports/`](reports), [`shared/`](shared) | Authoritative interface contract, unified runner (`run_reflectsort.py`), integration test harness, final reports. |

---

## 3. System Architecture & Data Flow

```
+-----------------------------------------------------------------------------------------+
|                                      ReflectSort                                        |
+-----------------------------------------------------------------------------------------+
|                                                                                         |
|  [Optical Sensor / Simulator]                                                           |
|       |                                                                                 |
|       | 12-bit ADC (sample_LDR, ambient_LDR, ref_value)                                 |
|       v                                                                                 |
|  [Input Validation & Feature Extraction]                                                |
|       | - Range checks [0, 4095], ambient > 0                                           |
|       | - 3-Feature Contract: [sample_LDR, ambient_LDR, sample/ambient ratio]           |
|       v                                                                                 |
|  [ML Inference Engine (Member 2 Model)]                                                 |
|       | - StandardScaler Preprocessing                                                  |
|       | - RandomForestClassifier (150 trees, seed=117)                                  |
|       | - Class output: Dark / Medium / Light                                           |
|       v                                                                                 |
|  [Bin Mapping & Confidence Policy]                                                      |
|       | - Dark -> BIN_A | Medium -> BIN_B | Light -> BIN_C                               |
|       | - Low confidence (< 60%) / Out-of-bounds -> HOLD                                |
|       v                                                                                 |
|  [Member 4 Decision Validator Safety Gate]                                              |
|       | - Checks request ID match, timestamp monotonicity, 2.0s timeout, replay filter  |
|       v                                                                                 |
|  [Actuator Simulator Diverter / Hardware Chute]                                         |
|       | - BIN_A (45°), BIN_B (90°), BIN_C (135°), HOLD / REJECT (90° / 180°)            |
|       v                                                                                 |
|  [Audit Logging & Display] (CSV Log + GUI History)                                      |
+-----------------------------------------------------------------------------------------+
```

---

## 4. Quickstart & Usage Instructions

### A. Environment Setup
```bash
cd ReflectSort_Integrated
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

### B. System Diagnostics
```bash
python3 run_reflectsort.py --check
```

### C. Single-Reading CLI Prediction
```bash
python3 run_reflectsort.py --cli 510 150 900
```
- Argument 1: Sample LDR reading (ADC counts)
- Argument 2: Ambient LDR reading (ADC counts)
- Argument 3 (Optional): Reference LDR baseline count

### D. Batch CSV Classification
```bash
python3 run_reflectsort.py --csv application/data/sample_readings.csv
```

### E. End-to-End Closed-Loop Simulation
```bash
python3 run_reflectsort.py --sim 5
```
Simulates 5 specimens through optical acquisition, ML inference, safety gate validation, and mechanical diverter actuation.

### F. Interactive Graphical User Interface
```bash
python3 run_reflectsort.py --gui
```

### G. Run Automated Test Suite
```bash
python3 -m pytest -v
```

---

## 5. Repository Structure

```text
ReflectSort_Integrated/
├── README.md                          # Top-level project guide
├── requirements.txt                   # Unified dependency specification
├── pyproject.toml                     # Packaging and pytest configuration
├── .gitignore                         # Clean version control exclusions
├── run_reflectsort.py                 # Top-level master runner
│
├── ml/                                # Member 2 (Kuldeep Singh)
│   ├── README.md                      # ML documentation and training instructions
│   ├── train_model.py                 # Model training pipeline
│   ├── generate_demo_data.py          # Synthetic dataset generator
│   ├── dataset_template.csv           # Labelled CSV template
│   ├── model/
│   │   └── shade_model.joblib         # Approved model artifact
│   ├── data/
│   │   ├── demo_data_simulated.csv    # 900 synthetic training rows
│   │   └── test_readings_expected.csv # Verification reference readings
│   └── outputs/                       # Evaluation reports, confusion matrix, metrics
│
├── application/                       # Member 3 (Satyam Rai)
│   ├── README.md                      # Application manual and GUI instructions
│   ├── shade_demo.py                  # Tkinter GUI and CLI application
│   ├── serial_reader.py               # Optional UART / serial communication bridge
│   ├── prediction_log.csv             # Execution audit log
│   └── data/
│       └── sample_readings.csv        # Batch verification CSV
│
├── member4_system/                    # Member 4 (Ajitesh Karan)
│   ├── README.md                      # Embedded architecture & simulation documentation
│   ├── interface_spec.md              # Detailed schema specification
│   ├── hardware_plan.md               # Hardware bill of materials and wiring
│   ├── firmware_design.md             # Future STM32 bare-metal / HAL design
│   ├── system_architecture.mmd        # Architecture diagram
│   ├── test_plan.md                   # Formal testing specification
│   ├── src/reflectsort_member4/       # Core modules (schemas, simulator, validator, actuator)
│   ├── examples/run_simulation.py     # 7-scenario simulation runner
│   └── tests/                         # Subsystem unit and regression test suite
│
├── shared/                            # Shared Contracts & Configurations
│   ├── interface_contract.md          # Authoritative system interface contract
│   └── configuration.py               # System constants, ADC limits, and mapping rules
│
├── tests/                             # Unified Integration Test Suite
│   ├── test_ml_integration.py         # ML model and pipeline integration tests
│   ├── test_application_integration.py# Application validation and batch tests
│   └── test_end_to_end.py             # End-to-end multi-layer pipeline tests
│
└── reports/                           # Project Reports & Documentation
    ├── ReflectSort_Final_Report.md    # Comprehensive master integration report
    ├── RUN_INSTRUCTIONS.md            # Detailed execution manual
    ├── HARDWARE_PENDING.md            # Physical hardware pending checklist
    ├── TEST_RESULTS.md                # Verification test results summary
    └── TEAM_CONTRIBUTIONS.md          # Member ownership & contribution breakdown
```

---

## 6. Future Hardware Roadmap

Phase 2 will interface the software pipeline with physical hardware:
- **MCU:** STM32 NUCLEO-F446RE (ARM Cortex-M4 @ 180 MHz)
- **Optical Sensors:** Dual LDR voltage divider circuits with white LED illumination chamber
- **Diverter:** TowerPro SG90 micro servo PWM control (50 Hz, 1.0–2.0 ms pulse width)
- **Communication:** USB-UART VCP at 115200 baud with NDJSON message framing

See [`reports/HARDWARE_PENDING.md`](reports/HARDWARE_PENDING.md) for the complete hardware implementation plan.
