#!/usr/bin/env python3
"""
ReflectSort — End-to-End Simulation Demonstration
File: examples/run_simulation.py

Demonstrates the Member 4 hardware-side simulation, protocol exchange,
safety validation, and diverter actuator response.

DISCLAIMER:
This demonstration executes purely in software. No physical STM32 microcontroller,
optical sensors, LEDs, or physical servo motors are connected.
The ML classification decisions in this script are explicitly supplied demonstration
fixtures to verify the hardware-side interface and safety gating logic.

Author: Ajitesh Karan (2500032236)
Course: Machine Learning – Embedded Systems Design (ML–ESD)
Team: ML-ESD-TEAM-117 (Project 12, Variant 06)
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

# Ensure package in src/ is on Python path regardless of execution directory
_script_dir = os.path.dirname(os.path.abspath(__file__))
_src_dir = os.path.abspath(os.path.join(_script_dir, "..", "src"))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from reflectsort_member4.actuator_simulator import (
    ActuatorConfig,
    ActuatorSimulator,
)
from reflectsort_member4.decision_validator import (
    DEFAULT_MAX_RESPONSE_LATENCY_SECONDS,
    DecisionValidator,
    DecisionValidatorConfig,
)
from reflectsort_member4.schemas import (
    DecisionRequest,
    DecisionResponse,
    SensorRecord,
    SortingDecision,
)
from reflectsort_member4.sensor_simulator import (
    SensorSimulator,
    SensorSimulatorConfig,
)


def print_banner() -> None:
    print("=" * 80)
    print("  REFLECTSORT — SENSOR-BASED GRAIN SHADE SORTING PROTOTYPE")
    print("  Member 4: System Architecture, Simulation & Validation Subsystem")
    print("  Author: Ajitesh Karan (2500032236) | Team: ML-ESD-TEAM-117")
    print("=" * 80)
    print("  [NOTICE] Pure software simulation running on macOS / Python 3.")
    print("  No physical STM32 NUCLEO-F446RE, LDR sensors, or servo hardware connected.")
    print("=" * 80)
    print()


def run_scenario(
    scenario_num: int,
    scenario_title: str,
    sensor_sim: SensorSimulator,
    validator: DecisionValidator,
    actuator: ActuatorSimulator,
    specimen_id: str,
    profile_name: str,
    proposed_label: str,
    confidence: Optional[float],
    simulate_delay_seconds: float = 0.05,
    force_mismatched_id: bool = False,
    use_raw_json_line: bool = False,
) -> None:
    print(f"--- [Scenario {scenario_num}]: {scenario_title} ---")

    # Establish logically consistent timestamps using validator's clock
    now = validator.clock() if hasattr(validator, "clock") else datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    else:
        now = now.astimezone(timezone.utc)

    # The optical acquisition and request dispatch occurred in the past by simulate_delay_seconds
    req_dt = now - timedelta(seconds=simulate_delay_seconds)
    req_ts = req_dt.isoformat()

    # Step 1: Simulate Optical Sensor Acquisition
    record = sensor_sim.generate_reading(
        specimen_id=specimen_id,
        run_id="DEMO-RUN-2026",
        profile_name=profile_name,
        timestamp=req_ts,
    )
    voltages = record.to_voltages(vref=3.30)
    print(f"  [Sensor Acquisition] Specimen: {record.specimen_id} | Profile Fixture: {profile_name}")
    print(f"    - Sample LDR:         {record.sample_LDR:7.2f} counts (12-bit, 0-4095) -> {voltages['sample_voltage_V']:.3f} V")
    print(f"    - Ambient LDR:        {record.ambient_LDR:7.2f} counts (12-bit, 0-4095) -> {voltages['ambient_voltage_V']:.3f} V")
    print(f"    - Reference Baseline: {record.reference_value:7.2f} counts (12-bit, 0-4095) -> {voltages['reference_voltage_V']:.3f} V")
    print(f"    - Differential LDR:   {record.derived_features.get('differential_LDR'):7.2f} counts")
    print(f"    - Contrast Ratio:     {record.derived_features.get('contrast_ratio'):7.4f}")
    print(f"    - Data Source Flag:   '{record.data_source}'")

    # Step 2: Format Request for Host / Python App
    req_id = f"REQ-{record.specimen_id}"
    req = DecisionRequest(
        request_id=req_id,
        features=record.to_model_features(),
        timestamp=record.timestamp,
        data_source="simulated",
    )

    # Step 3: Simulate Host / ML Model Response
    resp_req_id = "REQ-CORRUPTED-999" if force_mismatched_id else req_id
    # Response timestamp matches arrival time (req_dt + elapsed delay = now)
    resp_dt = now

    conf_str = f"{confidence:.2%}" if confidence is not None else "None (Omitted)"
    print(f"\n  [Host ML Decision Input] (Supplied demonstration decision):")
    print(f"    - Proposed Label:     {proposed_label}")
    print(f"    - Confidence Score:   {conf_str}")
    print(f"    - Response Request ID:{resp_req_id} (Expected: {req_id})")
    print(f"    - Simulated Latency:  {simulate_delay_seconds:.3f} s (Standard Timeout Limit: {validator.config.max_response_latency_seconds:.1f} s)")

    raw_response_dict = {
        "type": "decision",
        "request_id": resp_req_id,
        "label": proposed_label,
        "confidence": confidence,
        "timestamp": resp_dt.isoformat(),
    }
    raw_payload = json.dumps(raw_response_dict) if use_raw_json_line else raw_response_dict

    # Step 4: Decision Validation Gate
    val_result = validator.validate(
        response=raw_payload,
        expected_request_id=req_id,
        request_timestamp=record.timestamp,
    )

    print(f"\n  [Decision Validator Gate]:")
    print(f"    - Validated Status:   {'PASSED (Valid)' if val_result.is_valid else 'BLOCKED (Invalid/Safety Gate)'}")
    print(f"    - Action Permitted:   {val_result.validated_action.value}")
    print(f"    - Validation Reason:  {val_result.reason}")
    if val_result.error_code:
        print(f"    - Error Code:         {val_result.error_code}")

    # Step 5: Actuator Execution
    act_event = actuator.execute_decision(val_result)
    pos = actuator.get_current_position()
    print(f"\n  [Actuator Simulator Execution]:")
    print(f"    - Event ID:           {act_event.event_id}")
    print(f"    - Actuator State:     {pos['current_state']}")
    print(f"    - Previous Angle:     {act_event.previous_angle_deg:.1f}°")
    print(f"    - Resulting Angle:    {pos['current_angle_deg']:.1f}°")
    print(f"    - PWM Pulse Width:    {pos['estimated_pulse_width_ms']:.3f} ms (50 Hz PWM)")
    print(f"    - Execution Status:   {act_event.status}")
    print(f"    - Event Reason:       {act_event.reason}")
    print(f"    - Is Simulated:       {act_event.is_simulated}")
    print("-" * 80)
    print()


def main() -> None:
    print_banner()

    # Configure simulation components with standardized 2.0s timeout policy
    sensor_config = SensorSimulatorConfig(random_seed=101, noise_std_dev=10.0)
    sensor_sim = SensorSimulator(sensor_config)

    validator_config = DecisionValidatorConfig(
        max_response_latency_seconds=DEFAULT_MAX_RESPONSE_LATENCY_SECONDS,  # Standard 2.0s
        min_confidence_threshold=0.70,
        require_confidence=False,
    )
    validator = DecisionValidator(validator_config)

    actuator_config = ActuatorConfig(
        diverter_mode="THREE_BIN",
        min_travel_angle_deg=0.0,
        max_travel_angle_deg=180.0,
        home_angle_deg=90.0,
        reject_action_behavior="RETURN_TO_HOME",  # Safe neutral return on blocked decision
    )
    actuator = ActuatorSimulator(actuator_config)

    # Initial state
    print(f"[Initial System State] Actuator in Home Position: {actuator.current_angle_deg}° ({actuator.current_state})\n")

    # Scenario 1: Light Shade Grain -> Valid BIN_A
    run_scenario(
        scenario_num=1,
        scenario_title="Light Shade Grain Sample (Nominal High Reflectance)",
        sensor_sim=sensor_sim,
        validator=validator,
        actuator=actuator,
        specimen_id="GRAIN-001",
        profile_name="LIGHT_GRAIN",
        proposed_label="BIN_A",
        confidence=0.96,
        simulate_delay_seconds=0.12,
    )

    # Scenario 2: Medium Shade Grain -> Valid BIN_B
    run_scenario(
        scenario_num=2,
        scenario_title="Medium Shade Grain Sample (Moderate Reflectance)",
        sensor_sim=sensor_sim,
        validator=validator,
        actuator=actuator,
        specimen_id="GRAIN-002",
        profile_name="MEDIUM_GRAIN",
        proposed_label="BIN_B",
        confidence=0.91,
        simulate_delay_seconds=0.15,
    )

    # Scenario 3: Dark Shade Grain -> Valid BIN_C
    run_scenario(
        scenario_num=3,
        scenario_title="Dark / Discolored Grain Sample (Low Reflectance)",
        sensor_sim=sensor_sim,
        validator=validator,
        actuator=actuator,
        specimen_id="GRAIN-003",
        profile_name="DARK_GRAIN",
        proposed_label="BIN_C",
        confidence=0.94,
        simulate_delay_seconds=0.10,
    )

    # Scenario 4: Unknown / Foreign Object -> REJECT_UNKNOWN Chute
    run_scenario(
        scenario_num=4,
        scenario_title="Unidentifiable / Foreign Matter Sample",
        sensor_sim=sensor_sim,
        validator=validator,
        actuator=actuator,
        specimen_id="GRAIN-004",
        profile_name="DARK_GRAIN",
        proposed_label="REJECT_UNKNOWN",
        confidence=0.88,
        simulate_delay_seconds=0.08,
    )

    # Scenario 5: Safety Violation — Host Response Timeout / Expired (> 2.0s standard limit)
    run_scenario(
        scenario_num=5,
        scenario_title="Communication Stale / Timeout Violation (Simulated Latency > 2.0s)",
        sensor_sim=sensor_sim,
        validator=validator,
        actuator=actuator,
        specimen_id="GRAIN-005",
        profile_name="LIGHT_GRAIN",
        proposed_label="BIN_A",
        confidence=0.98,
        simulate_delay_seconds=2.85,  # Exceeds 2.0s timeout limit!
    )

    # Scenario 6: Safety Violation — Unsupported / Unrecognized Classification Label
    run_scenario(
        scenario_num=6,
        scenario_title="Host Sent Unregistered Label Category ('BIN_PREMIUM_GOLD')",
        sensor_sim=sensor_sim,
        validator=validator,
        actuator=actuator,
        specimen_id="GRAIN-006",
        profile_name="MEDIUM_GRAIN",
        proposed_label="BIN_PREMIUM_GOLD",  # Unsupported
        confidence=0.90,
        simulate_delay_seconds=0.11,
    )

    # Scenario 7: Safety Violation — Mismatched Request Identifier
    run_scenario(
        scenario_num=7,
        scenario_title="Mismatched / Out-of-Order Request Identifier",
        sensor_sim=sensor_sim,
        validator=validator,
        actuator=actuator,
        specimen_id="GRAIN-007",
        profile_name="DARK_GRAIN",
        proposed_label="BIN_C",
        confidence=0.93,
        simulate_delay_seconds=0.09,
        force_mismatched_id=True,
    )

    # Summary of Actuator Audit Log
    print("=" * 80)
    print("  SIMULATED ACTUATOR AUDIT LOG (Chronological Event History)")
    print("=" * 80)
    history = actuator.get_history()
    print(f"{'Event ID':<16} | {'Request ID':<16} | {'Status':<10} | {'Prev':<6} | {'Target':<6} | {'Reason'}")
    print("-" * 80)
    for evt in history:
        print(f"{evt.event_id:<16} | {evt.request_id:<16} | {evt.status:<10} | {evt.previous_angle_deg:>5.1f}° | {evt.target_angle_deg:>5.1f}° | {evt.reason}")
    print("=" * 80)
    print("\nDemonstration completed successfully.")


if __name__ == "__main__":
    main()
