"""
ReflectSort — Unit & Integration Tests for Actuator Simulator
Test Module: tests.test_actuator_simulator

Author: Ajitesh Karan (2500032236)
Course: Machine Learning – Embedded Systems Design (ML–ESD)
Team: ML-ESD-TEAM-117 (Project 12, Variant 06)
"""

import pytest
from datetime import datetime, timezone

from reflectsort_member4.actuator_simulator import ActuatorConfig, ActuatorSimulator
from reflectsort_member4.decision_validator import (
    DecisionValidator,
    DecisionValidatorConfig,
    ValidationResult,
)
from reflectsort_member4.schemas import (
    DecisionRequest,
    DecisionResponse,
    SensorRecord,
    SortingDecision,
    ValidationError,
)
from reflectsort_member4.sensor_simulator import (
    SensorSimulator,
    SensorSimulatorConfig,
)


def test_actuator_initial_home_state() -> None:
    """Verify actuator starts in neutral home position (90 degrees, 1.5ms pulse width)."""
    actuator = ActuatorSimulator()
    pos = actuator.get_current_position()
    assert pos["current_angle_deg"] == 90.0
    assert pos["estimated_pulse_width_ms"] == pytest.approx(1.500)
    assert pos["current_state"] == "HOME_HOLD"
    assert pos["is_simulated"] is True


def test_pulse_width_mapping() -> None:
    """Verify 50Hz PWM pulse width calculation from angular positions."""
    actuator = ActuatorSimulator()
    assert actuator.angle_to_pulse_width_ms(0.0) == pytest.approx(1.000)
    assert actuator.angle_to_pulse_width_ms(45.0) == pytest.approx(1.250)
    assert actuator.angle_to_pulse_width_ms(90.0) == pytest.approx(1.500)
    assert actuator.angle_to_pulse_width_ms(135.0) == pytest.approx(1.750)
    assert actuator.angle_to_pulse_width_ms(180.0) == pytest.approx(2.000)


def test_accepted_bin_actions_map_to_correct_angles() -> None:
    """Verify that validated BIN_A, BIN_B, BIN_C map to configured diverter angles."""
    actuator = ActuatorSimulator()

    # BIN_A -> 45 deg
    val_a = ValidationResult(
        is_valid=True,
        validated_action=SortingDecision.BIN_A,
        request_id="REQ-01",
        reason="OK",
    )
    evt_a = actuator.execute_decision(val_a)
    assert evt_a.status == "EXECUTED"
    assert evt_a.target_angle_deg == 45.0
    assert actuator.current_angle_deg == 45.0
    assert actuator.current_state == "DIVERT_BIN_A"
    assert evt_a.is_simulated is True

    # BIN_C -> 135 deg
    val_c = ValidationResult(
        is_valid=True,
        validated_action=SortingDecision.BIN_C,
        request_id="REQ-02",
        reason="OK",
    )
    evt_c = actuator.execute_decision(val_c)
    assert evt_c.status == "EXECUTED"
    assert evt_c.target_angle_deg == 135.0
    assert actuator.current_angle_deg == 135.0
    assert actuator.current_state == "DIVERT_BIN_C"


def test_reject_unknown_moves_to_reject_chute() -> None:
    """Verify that REJECT_UNKNOWN diverts to configured reject angle (165 deg)."""
    actuator = ActuatorSimulator()
    val_reject = ValidationResult(
        is_valid=True,
        validated_action=SortingDecision.REJECT_UNKNOWN,
        request_id="REQ-REJ",
        reason="Unclassifiable sample",
    )
    evt = actuator.execute_decision(val_reject)
    assert evt.status == "EXECUTED"
    assert evt.target_angle_deg == 165.0
    assert actuator.current_angle_deg == 165.0
    assert actuator.current_state == "DIVERT_REJECT_UNKNOWN"


def test_hold_action_returns_to_home() -> None:
    """Verify that a valid HOLD command returns actuator to neutral home angle (90 deg)."""
    actuator = ActuatorSimulator()
    # First move to Bin A
    actuator.execute_decision(
        ValidationResult(is_valid=True, validated_action=SortingDecision.BIN_A, request_id="R1", reason="OK")
    )
    assert actuator.current_angle_deg == 45.0

    # Now execute HOLD
    val_hold = ValidationResult(
        is_valid=True,
        validated_action=SortingDecision.HOLD,
        request_id="R2",
        reason="Holding",
    )
    evt_hold = actuator.execute_decision(val_hold)
    assert evt_hold.status == "HELD"
    assert evt_hold.target_angle_deg == 90.0
    assert actuator.current_angle_deg == 90.0
    assert actuator.current_state == "HOLD_NEUTRAL"


def test_invalid_validation_result_safe_state_consistency() -> None:
    """
    Verify state consistency upon receiving an invalid validation result:
    1. Default RETURN_TO_HOME policy: returns to 90°, updates state to SAFETY_BLOCKED_HOME
    2. FREEZE_CURRENT policy: holds angle, updates state to SAFETY_BLOCKED_FROZEN
    """
    # 1. Default RETURN_TO_HOME behavior
    actuator_home = ActuatorSimulator(ActuatorConfig(reject_action_behavior="RETURN_TO_HOME"))
    # Move to Bin C (135 deg)
    actuator_home.execute_decision(
        ValidationResult(is_valid=True, validated_action=SortingDecision.BIN_C, request_id="R1", reason="OK")
    )
    assert actuator_home.current_angle_deg == 135.0

    # An expired response arrives
    val_expired = ValidationResult(
        is_valid=False,
        validated_action=SortingDecision.HOLD,
        request_id="R-EXPIRED",
        reason="Timeout exceeded",
        error_code="ERR_RESPONSE_EXPIRED",
    )
    evt1 = actuator_home.execute_decision(val_expired)
    assert evt1.status == "REJECTED"
    assert actuator_home.current_angle_deg == 90.0
    assert actuator_home.current_state == "SAFETY_BLOCKED_HOME"
    assert "BLOCKED" in actuator_home.last_decision

    # 2. FREEZE_CURRENT behavior
    actuator_freeze = ActuatorSimulator(ActuatorConfig(reject_action_behavior="FREEZE_CURRENT"))
    actuator_freeze.execute_decision(
        ValidationResult(is_valid=True, validated_action=SortingDecision.BIN_C, request_id="R2", reason="OK")
    )
    assert actuator_freeze.current_angle_deg == 135.0

    evt2 = actuator_freeze.execute_decision(val_expired)
    assert evt2.status == "REJECTED"
    assert actuator_freeze.current_angle_deg == 135.0
    assert actuator_freeze.current_state == "SAFETY_BLOCKED_FROZEN"


def test_actuator_config_travel_limits_validation() -> None:
    """Verify rejection of invalid actuator configuration parameters."""
    with pytest.raises(ValidationError):
        ActuatorConfig(min_travel_angle_deg=100, max_travel_angle_deg=50).validate()
    with pytest.raises(ValidationError):
        ActuatorConfig(home_angle_deg=200).validate()
    with pytest.raises(ValidationError):
        ActuatorConfig(reject_action_behavior="INVALID_BEHAVIOR").validate()


def test_actuator_history_tracking_and_clearing() -> None:
    """Verify that action history accumulates events correctly and can be reset."""
    actuator = ActuatorSimulator()
    assert len(actuator.get_history()) == 0

    actuator.execute_decision(
        ValidationResult(is_valid=True, validated_action=SortingDecision.BIN_A, request_id="R1", reason="OK")
    )
    actuator.execute_decision(
        ValidationResult(is_valid=True, validated_action=SortingDecision.BIN_B, request_id="R2", reason="OK")
    )
    actuator.home()

    history = actuator.get_history()
    assert len(history) == 3
    assert history[0].decision == "BIN_A"
    assert history[1].decision == "BIN_B"
    assert history[2].status == "HELD"

    actuator.clear_history()
    assert len(actuator.get_history()) == 0


# ============================================================================
# End-to-End Pipeline Integration Test
# ============================================================================

def test_full_software_simulation_pipeline_integration() -> None:
    """
    Integration Test:
    1. SensorSimulator generates a synthetic measurement record.
    2. Record passes Schema validation and computes derived features.
    3. DecisionRequest is formatted for host ML layer (with JSON line export).
    4. Host application returns a DecisionResponse.
    5. DecisionValidator verifies schema, request ID, freshness, and label.
    6. ActuatorSimulator executes the validated command safely.
    """
    # 1. Initialize simulation modules
    sensor_sim = SensorSimulator(SensorSimulatorConfig(random_seed=42))
    validator = DecisionValidator(DecisionValidatorConfig(max_response_latency_seconds=2.0))
    actuator = ActuatorSimulator()

    # 2. Acquire simulated sensor record
    record = sensor_sim.generate_reading(
        specimen_id="SEED-INTEG-001",
        run_id="INTEG-RUN-01",
        profile_name="LIGHT_GRAIN",
    )
    assert record.data_source == "simulated"
    record.validate()

    # 3. Create host decision request
    req = DecisionRequest(
        request_id=f"REQ-{record.specimen_id}",
        features=record.to_model_features(),
        timestamp=record.timestamp,
        data_source="simulated",
    )
    req_json_line = req.to_json_line()
    assert "REQ-SEED-INTEG-001" in req_json_line

    # 4. Simulate host ML model response (e.g. Light grain -> BIN_A)
    resp = DecisionResponse(
        request_id=req.request_id,
        label="BIN_A",
        confidence=0.96,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    resp.validate()

    # 5. Validate decision on hardware/controller layer
    val_res = validator.validate(
        response=resp,
        expected_request_id=req.request_id,
        request_timestamp=req.timestamp,
    )
    assert val_res.is_valid is True
    assert val_res.validated_action == SortingDecision.BIN_A

    # 6. Actuator executes decision
    act_event = actuator.execute_decision(val_res)
    assert act_event.status == "EXECUTED"
    assert act_event.target_angle_deg == 45.0
    assert actuator.current_angle_deg == 45.0
    assert actuator.current_state == "DIVERT_BIN_A"
    assert act_event.is_simulated is True
