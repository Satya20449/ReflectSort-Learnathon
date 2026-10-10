"""
Unit & Regression tests for End-to-End Simulation Demonstration
File: tests/test_simulation_regression.py

Author: Ajitesh Karan (2500032236)
Course: Machine Learning – Embedded Systems Design (ML–ESD)
Team: ML-ESD-TEAM-117 (Project 12, Variant 06)
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from reflectsort_member4.actuator_simulator import ActuatorSimulator
from reflectsort_member4.decision_validator import (
    DecisionValidator,
    DecisionValidatorConfig,
)
from reflectsort_member4.sensor_simulator import SensorSimulator


def test_simulation_script_execution_via_subprocess():
    """
    Test that run_simulation.py executes to completion with exit code 0
    when run from the member4_system directory.
    """
    member4_dir = Path(__file__).resolve().parent.parent
    script_path = member4_dir / "examples" / "run_simulation.py"
    assert script_path.exists(), f"Missing script at {script_path}"

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(member4_dir),
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert result.returncode == 0, f"run_simulation.py failed with stderr:\n{result.stderr}"
    assert "Demonstration completed successfully." in result.stdout
    assert "Scenario 1" in result.stdout
    assert "Scenario 7" in result.stdout
    assert "SIMULATED ACTUATOR AUDIT LOG" in result.stdout


def test_simulation_main_direct_call(capsys):
    """
    Test that importing and executing main() from run_simulation runs cleanly.
    """
    from examples.run_simulation import main

    main()
    captured = capsys.readouterr()
    assert "REFLECTSORT — SENSOR-BASED GRAIN SHADE SORTING PROTOTYPE" in captured.out
    assert "Demonstration completed successfully." in captured.out


def test_simulation_scenarios_logic():
    """
    Verify core logic tested across all 7 scenarios in run_simulation.
    """
    from examples.run_simulation import run_scenario

    sensor_sim = SensorSimulator()
    validator = DecisionValidator(
        DecisionValidatorConfig(
            min_confidence_threshold=0.70,
            require_confidence=False,
        )
    )
    actuator = ActuatorSimulator()

    # Scenario 1: Valid LIGHT_GRAIN -> BIN_A
    run_scenario(
        scenario_num=1,
        scenario_title="Nominal Light Grain",
        sensor_sim=sensor_sim,
        validator=validator,
        actuator=actuator,
        specimen_id="REG-001",
        profile_name="LIGHT_GRAIN",
        proposed_label="BIN_A",
        confidence=0.96,
        simulate_delay_seconds=0.01,
    )
    last_event = actuator.get_history()[-1]
    assert last_event.status == "EXECUTED"
    assert last_event.target_angle_deg == 45.0

    # Scenario 4: Low confidence rejection (< 0.70 threshold)
    run_scenario(
        scenario_num=4,
        scenario_title="Low Confidence Rejection",
        sensor_sim=sensor_sim,
        validator=validator,
        actuator=actuator,
        specimen_id="REG-004",
        profile_name="DARK_GRAIN",
        proposed_label="BIN_C",
        confidence=0.62,
        simulate_delay_seconds=0.01,
    )
    last_event = actuator.get_history()[-1]
    assert last_event.status == "REJECTED"
    assert last_event.target_angle_deg == 90.0
    assert actuator.current_state == "SAFETY_BLOCKED_HOME"

    # Scenario 5: Response timeout (> 2.0s) -> ERR_RESPONSE_EXPIRED
    run_scenario(
        scenario_num=5,
        scenario_title="Response Timeout",
        sensor_sim=sensor_sim,
        validator=validator,
        actuator=actuator,
        specimen_id="REG-005",
        profile_name="LIGHT_GRAIN",
        proposed_label="BIN_A",
        confidence=0.98,
        simulate_delay_seconds=2.85,
    )
    last_event = actuator.get_history()[-1]
    assert last_event.status == "REJECTED"
    assert last_event.target_angle_deg == 90.0
    assert "expired" in last_event.reason.lower()
    assert actuator.current_state == "SAFETY_BLOCKED_HOME"
