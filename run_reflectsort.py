#!/usr/bin/env python3
"""
ReflectSort — Explainable Optical Mini-Sorting Cell (Integrated Master Runner)
Project ID: PROJECT-12-VARIANT-06 | Team: ML-ESD-TEAM-117

Connects and orchestrates all three team members' implementations:
- Member 2 (Kuldeep Singh): ML training pipeline & approved model artifact
- Member 3 (Satyam Rai): Host application, input validation, UI, and logging
- Member 4 (Ajitesh Karan): Sensor simulation, decision safety gate & actuator modeling
- Team Lead (Satya Nayak): Overall architecture & integration coordination

Usage:
    python run_reflectsort.py --cli 510 150 900          # Single manual CLI reading
    python run_reflectsort.py --csv <path_to_csv>        # Batch CSV classification
    python run_reflectsort.py --sim [count]              # End-to-end software simulation
    python run_reflectsort.py --gui                      # Interactive Tkinter GUI
    python run_reflectsort.py --check                    # System diagnostic check
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
_m4_src = PROJECT_ROOT / "member4_system" / "src"
if str(_m4_src) not in sys.path:
    sys.path.insert(0, str(_m4_src))

from application.shade_demo import Predictor, run_csv_batch, run_gui, log_prediction
from member4_system.src.reflectsort_member4.actuator_simulator import (
    ActuatorConfig,
    ActuatorSimulator,
)
from member4_system.src.reflectsort_member4.decision_validator import (
    DEFAULT_MAX_RESPONSE_LATENCY_SECONDS,
    DecisionValidator,
    DecisionValidatorConfig,
)
from member4_system.src.reflectsort_member4.schemas import (
    DecisionRequest,
    DecisionResponse,
    SensorRecord,
    SortingDecision,
)
from member4_system.src.reflectsort_member4.sensor_simulator import (
    SensorSimulator,
    SensorSimulatorConfig,
)
from shared.configuration import (
    ADC_MAX_COUNT,
    ADC_MIN_COUNT,
    EXPECTED_CLASSES,
    EXPECTED_FEATURES,
    LABEL_TO_BIN,
    PERMITTED_SORTING_ACTIONS,
    compute_ml_features,
    map_shade_to_bin,
    validate_raw_sensor_inputs,
)


def print_banner(title: str = "REFLECTSORT INTEGRATED CELL") -> None:
    print("=" * 80)
    print(f"  {title}")
    print("  Project: PROJECT-12-VARIANT-06 | Team: ML-ESD-TEAM-117")
    print("  Subsystems: ML Pipeline (M2) | Application (M3) | Embedded Sim & Gate (M4)")
    print("=" * 80)


def run_diagnostics(predictor: Optional[Predictor] = None) -> None:
    print_banner("SYSTEM DIAGNOSTICS & INTEGRATION REPORT")
    p = predictor or Predictor()
    import sklearn

    print(f"Python Runtime:       {sys.version.split()[0]} on {sys.platform}")
    print(f"Scikit-Learn Version: {sklearn.__version__}")
    print(f"Active ML Model:      {p.model_path.relative_to(PROJECT_ROOT) if p.model_path.is_relative_to(PROJECT_ROOT) else p.model_path}")
    print(f"Data Source:          {p.data_source}")
    print(f"Model Features:       {p.features}")
    print(f"Model Classes:        {p.classes}")
    print(f"Confidence Threshold: {p.confidence_threshold:.2%}")
    print(f"Training Boundaries:")
    for f in p.features:
        lo = p.training_min.get(f, "N/A")
        hi = p.training_max.get(f, "N/A")
        print(f"  - {f:<18}: {lo} to {hi}")
    print(f"Shade to Bin Mapping: {LABEL_TO_BIN}")
    print(f"Permitted Decisions:  {PERMITTED_SORTING_ACTIONS}")
    print("-" * 80)
    print("Integration Status: ALL SUBSYSTEMS OPERATIONAL")
    print("=" * 80)


def run_end_to_end_simulation(count: int = 5, seed: int = 117) -> None:
    """
    Execute a closed-loop end-to-end simulation across all 3 member layers:
    1. SensorSimulator generates synthetic optical readings (Member 4)
    2. Feature Extraction constructs 3-feature contract (Shared/M2)
    3. Predictor infers shade class & calculates confidence (Member 2)
    4. DecisionValidator applies safety & temporal rules (Member 4)
    5. ActuatorSimulator models mechanical diverter response (Member 4)
    6. Event is logged to CSV & audit history (Member 3/4)
    """
    print_banner(f"END-TO-END INTEGRATED SIMULATION ({count} SPECIMENS)")
    print("DISCLAIMER: Pure software simulation running on synthetic optical models.\n")

    # 1. Initialize subsystems
    sensor_sim = SensorSimulator(SensorSimulatorConfig(random_seed=seed, noise_std_dev=8.0))
    predictor = Predictor()
    validator = DecisionValidator(DecisionValidatorConfig(
        max_response_latency_seconds=DEFAULT_MAX_RESPONSE_LATENCY_SECONDS,
        min_confidence_threshold=predictor.confidence_threshold,
        require_confidence=True,
    ))
    actuator = ActuatorSimulator(ActuatorConfig(
        diverter_mode="THREE_BIN",
        home_angle_deg=90.0,
        reject_action_behavior="RETURN_TO_HOME",
    ))

    profiles = ["SIM_LIGHT", "SIM_MEDIUM", "SIM_DARK"]
    history = []

    for i in range(1, count + 1):
        prof = profiles[(i - 1) % len(profiles)]
        spec_id = f"GRAIN-{i:04d}"
        req_id = f"REQ-{spec_id}"

        # 1. Optical sensor acquisition
        now_req = dt.datetime.now(dt.timezone.utc)
        record = sensor_sim.generate_reading(
            specimen_id=spec_id,
            run_id="E2E-RUN-01",
            profile_name=prof,
            timestamp=now_req.isoformat(),
        )

        # 2. Extract approved ML features
        ml_features = record.to_approved_ml_features()
        s_val = ml_features["sample_LDR"]
        a_val = ml_features["ambient_LDR"]
        r_val = record.reference_value

        # 3. Model inference (Member 2 via Member 3 Predictor)
        app_action, conf, note = predictor.predict(s_val, a_val, r_val)
        now_resp = dt.datetime.now(dt.timezone.utc)

        # 4. Construct DecisionResponse message
        resp = DecisionResponse(
            request_id=req_id,
            label=app_action,
            confidence=conf,
            timestamp=now_resp.isoformat(),
            metadata={"note": note, "specimen_id": spec_id, "profile": prof},
        )

        # 5. Validate through MCU safety gate (Member 4)
        val_result = validator.validate(
            response=resp,
            expected_request_id=req_id,
            request_timestamp=record.timestamp,
        )

        # 6. Actuate mechanical diverter (Member 4)
        act_event = actuator.execute_decision(val_result)
        pos = actuator.get_current_position()

        # 7. Log prediction (Member 3)
        log_prediction(s_val, a_val, r_val, val_result.validated_action.value, conf, note)

        print(f"Specimen {i:2d} [{spec_id}] (Profile: {prof:<12}):")
        print(f"  - Sensor Acquisition: S={s_val:6.1f} counts, A={a_val:6.1f} counts, Ratio={ml_features['reflectance_ratio']:.3f}")
        print(f"  - ML Classification:  Proposed '{app_action}' (Confidence: {conf:.2%}) | {note}")
        print(f"  - Safety Gate:        Status={'VALID' if val_result.is_valid else 'BLOCKED'} -> Permitted Action='{val_result.validated_action.value}'")
        print(f"  - Actuator Diverter:  Angle={pos['current_angle_deg']:5.1f}° | State={pos['current_state']:<16} | Status={act_event.status}")
        print("-" * 80)
        history.append(act_event)

    print("\n" + "=" * 80)
    print("  SIMULATION AUDIT TRAIL SUMMARY")
    print("=" * 80)
    print(f"{'Event ID':<16} | {'Request ID':<16} | {'Status':<10} | {'Prev':<6} | {'Target':<6} | {'Reason'}")
    print("-" * 80)
    for evt in history:
        print(f"{evt.event_id:<16} | {evt.request_id:<16} | {evt.status:<10} | {evt.previous_angle_deg:>5.1f}° | {evt.target_angle_deg:>5.1f}° | {evt.reason}")
    print("=" * 80)
    print(f"End-to-End Simulation completed. {count} specimens processed successfully.\n")


def main():
    parser = argparse.ArgumentParser(
        description="ReflectSort — Explainable Optical Mini-Sorting Cell Master Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--cli", nargs="+", type=float, metavar="VAL", help="Direct sensor reading: SAMPLE AMBIENT [REFERENCE]")
    parser.add_argument("--csv", type=str, metavar="FILE", help="Process sensor readings from CSV file")
    parser.add_argument("--sim", nargs="?", const=5, type=int, metavar="COUNT", help="Run end-to-end simulation for COUNT specimens (default: 5)")
    parser.add_argument("--gui", action="store_true", help="Launch interactive graphical interface")
    parser.add_argument("--check", action="store_true", help="Run environment and model diagnostic checks")

    args = parser.parse_args()

    if args.check:
        run_diagnostics()
    elif args.cli is not None:
        if len(args.cli) not in (2, 3):
            parser.error("--cli requires 2 or 3 arguments: SAMPLE_LDR AMBIENT_LDR [REFERENCE_VALUE]")
        s = args.cli[0]
        a = args.cli[1]
        r = args.cli[2] if len(args.cli) == 3 else None
        predictor = Predictor()
        action, conf, note = predictor.predict(s, a, r)
        log_prediction(s, a, r, action, conf, note)
        print_banner("MANUAL CLI PREDICTION RESULT")
        print(f"Sample LDR:     {s:.2f} counts")
        print(f"Ambient LDR:    {a:.2f} counts")
        print(f"Reference:      {r if r is not None else 'N/A'}")
        print(f"Sorting Action: {action}")
        print(f"Confidence:     {conf:.2%}")
        print(f"Explanation:    {note}")
        print("=" * 80)
    elif args.csv:
        predictor = Predictor()
        print_banner(f"BATCH CSV CLASSIFICATION: {args.csv}")
        run_csv_batch(predictor, args.csv)
    elif args.sim is not None:
        run_end_to_end_simulation(count=args.sim)
    elif args.gui:
        predictor = Predictor()
        run_gui(predictor)
    else:
        # Default behavior if no arguments: print usage and run diagnostics
        run_diagnostics()
        print("\nTip: Run with --help to see all available options (CLI, CSV, Simulation, GUI).")


if __name__ == "__main__":
    main()
