# ReflectSort — Team Ownership and Contribution Breakdown

**Project ID:** `PROJECT-12-VARIANT-06`  
**Project Title:** ReflectSort — Explainable Optical Mini-Sorting Cell  
**Team Designation:** `ML-ESD-TEAM-117`  
**Institution:** KL University — Machine Learning – Embedded Systems Design (ML-ESD)

---

## 1. Team Roster and Responsibilities Overview

| Member Name | Role & Subsystem Ownership | Core Deliverables |
|---|---|---|
| **Kuldeep Singh** | **Member 2** — Machine Learning Pipeline, Dataset & Modeling | Training pipeline, synthetic dataset generator, approved model bundle, evaluation metrics and reports. |
| **Satyam Rai** | **Member 3** — Python Software Application & User Interface | Host application GUI (Tkinter), CLI interface, input validation gate, batch CSV classifier, serial bridge, execution logging. |
| **Ajitesh Karan** | **Member 4** — System Architecture, Simulation & Validation | System architecture, sensor simulation, 8-rule decision safety gate, diverter actuator physics model, subsystem unit/regression tests, embedded firmware design. |
| **Satya Nayak** | **Team Lead** — Integration Coordination & Final Delivery | Unified repository integration, authoritative interface contracts, master runner (`run_reflectsort.py`), end-to-end integration test harness, packaging, and final reports. |

---

## 2. Granular File-to-Member Ownership Mapping

```text
ReflectSort_Integrated/
├── README.md                                 <- Satya Nayak (Lead Integration)
├── requirements.txt                          <- Satya Nayak (Unified Dependencies)
├── pyproject.toml                            <- Satya Nayak (Packaging Config)
├── .gitignore                                <- Satya Nayak (Repository Hygiene)
├── run_reflectsort.py                        <- Satya Nayak (Integrated Master Runner)
│
├── ml/                                       <- Member 2: Kuldeep Singh
│   ├── README.md                             <- Kuldeep Singh
│   ├── train_model.py                        <- Kuldeep Singh
│   ├── generate_demo_data.py                 <- Kuldeep Singh
│   ├── dataset_template.csv                  <- Kuldeep Singh
│   ├── model/
│   │   └── shade_model.joblib                <- Kuldeep Singh (Approved ML Model Artifact)
│   ├── data/
│   │   ├── demo_data_simulated.csv           <- Kuldeep Singh (Synthetic Dataset)
│   │   └── test_readings_expected.csv        <- Kuldeep Singh
│   └── outputs/
│       ├── evaluation_summary.json           <- Kuldeep Singh
│       ├── training_evaluation_report.md     <- Kuldeep Singh
│       ├── classification_report.txt         <- Kuldeep Singh
│       ├── confusion_matrix.csv              <- Kuldeep Singh
│       └── sample_predictions.csv            <- Kuldeep Singh
│
├── application/                              <- Member 3: Satyam Rai
│   ├── README.md                             <- Satyam Rai
│   ├── shade_demo.py                         <- Satyam Rai
│   ├── serial_reader.py                      <- Satyam Rai
│   ├── prediction_log.csv                    <- Satyam Rai
│   └── data/
│       └── sample_readings.csv               <- Satyam Rai
│
├── member4_system/                           <- Member 4: Ajitesh Karan
│   ├── README.md                             <- Ajitesh Karan
│   ├── interface_spec.md                     <- Ajitesh Karan
│   ├── hardware_plan.md                      <- Ajitesh Karan
│   ├── firmware_design.md                    <- Ajitesh Karan
│   ├── system_architecture.mmd               <- Ajitesh Karan
│   ├── test_plan.md                          <- Ajitesh Karan
│   ├── src/reflectsort_member4/
│   │   ├── __init__.py                       <- Ajitesh Karan
│   │   ├── schemas.py                        <- Ajitesh Karan
│   │   ├── sensor_simulator.py               <- Ajitesh Karan
│   │   ├── decision_validator.py             <- Ajitesh Karan
│   │   └── actuator_simulator.py             <- Ajitesh Karan
│   ├── examples/
│   │   └── run_simulation.py                 <- Ajitesh Karan
│   └── tests/
│       ├── __init__.py                       <- Ajitesh Karan
│       ├── test_schemas.py                   <- Ajitesh Karan
│       ├── test_sensor_simulator.py          <- Ajitesh Karan
│       ├── test_decision_validator.py        <- Ajitesh Karan
│       ├── test_actuator_simulator.py        <- Ajitesh Karan
│       └── test_simulation_regression.py     <- Ajitesh Karan
│
├── shared/                                   <- Joint Team Shared Interfaces
│   ├── interface_contract.md                 <- Unified (Reconciled from M2, M3, M4)
│   └── configuration.py                      <- Unified System Constants & Bounds
│
├── tests/                                    <- Integration QA Suite (Satya Nayak & Team)
│   ├── __init__.py
│   ├── test_ml_integration.py                <- ML Model Verification Tests
│   ├── test_application_integration.py       <- Application UI & CSV Batch Tests
│   └── test_end_to_end.py                    <- Closed-Loop Multi-Layer Integration Tests
│
└── reports/                                  <- Integration Reports & Delivery Artifacts
    ├── ReflectSort_Final_Report.md           <- Comprehensive Integration Report
    ├── RUN_INSTRUCTIONS.md                   <- Execution Manual
    ├── HARDWARE_PENDING.md                   <- Phase 2 Hardware Checklist
    ├── TEST_RESULTS.md                       <- Automated Test Execution Log
    └── TEAM_CONTRIBUTIONS.md                 <- This Document
```

---

## 3. Provenance and Source Selection Summary

1. **Member 2 (Kuldeep Singh):**
   - Source: `ReflectSort_Integration_Review_Final.zip`
   - Retained the legitimate `train_model.py` pipeline, synthetic dataset generator `generate_demo_data.py`, and the approved `shade_model.joblib` bundle.
   - Features: `['sample_LDR', 'ambient_LDR', 'reflectance_ratio']`.

2. **Member 3 (Satyam Rai):**
   - Source: `seed_grain_shade_demo_FINAL (1).zip` with Kuldeep's reviewed improvements.
   - Retained Tkinter GUI application, CLI runner, ADC input validation ($[0, 4095]$), batch CSV mode, and serial bridge.
   - Replaced temporary/dummy model generation with native loading of Kuldeep's approved model artifact.

3. **Member 4 (Ajitesh Karan):**
   - Source: `ReflectSort(1).zip` -> `member4_system/`
   - Retained complete `reflectsort_member4` architecture package, schemas, sensor simulator, 8-rule decision validator, and actuator simulator.
   - Preserved all 62 subsystem tests and 7-scenario software demonstration harness.

4. **Integration Coordination (Satya Nayak):**
   - Harmonized feature contracts across modules.
   - Built unified master CLI (`run_reflectsort.py`) supporting all user modes (`--cli`, `--csv`, `--sim`, `--gui`, `--check`).
   - Created 30 unified multi-layer integration tests covering all failure modes, timeouts, clock drifts, and boundary conditions.
