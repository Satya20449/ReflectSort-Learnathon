"""
ReflectSort — Unit Tests for Schemas and Validation Rules
Test Module: tests.test_schemas

Author: Ajitesh Karan (2500032236)
Course: Machine Learning – Embedded Systems Design (ML–ESD)
Team: ML-ESD-TEAM-117 (Project 12, Variant 06)
"""

import math
import pytest
from datetime import datetime, timezone

from reflectsort_member4.schemas import (
    ActuatorEvent,
    DecisionRequest,
    DecisionResponse,
    InvalidNumericValueError,
    MalformedMessageError,
    SensorRecord,
    SortingDecision,
    ValidationError,
)


def test_valid_sensor_record_creation() -> None:
    """Verify that a well-formed SensorRecord is instantiated and validated successfully."""
    ts = datetime.now(timezone.utc).isoformat()
    record = SensorRecord(
        specimen_id="SEED-001",
        run_id="RUN-TEST-01",
        sample_LDR=2250.5,
        ambient_LDR=850.0,
        reference_value=2400.0,
        sample_position="tray_slot_1",
        angle=45.0,
        LED_setting="WHITE_100PCT",
        timestamp=ts,
        data_source="simulated",
    )
    assert record.specimen_id == "SEED-001"
    assert record.run_id == "RUN-TEST-01"
    assert record.sample_LDR == 2250.5
    assert record.ambient_LDR == 850.0
    assert record.reference_value == 2400.0
    assert record.sample_position == "tray_slot_1"
    assert record.angle == 45.0
    assert record.LED_setting == "WHITE_100PCT"
    assert record.data_source == "simulated"


def test_derived_features_computation() -> None:
    """Verify calculation of derived differential and contrast features."""
    ts = datetime.now(timezone.utc).isoformat()
    record = SensorRecord(
        specimen_id="SEED-002",
        run_id="RUN-TEST-01",
        sample_LDR=2850.0,
        ambient_LDR=850.0,
        reference_value=2000.0,
        sample_position="center",
        angle=45.0,
        LED_setting="WHITE_100PCT",
        timestamp=ts,
    )
    derived = record.compute_standard_derived_features()
    assert derived["differential_LDR"] == pytest.approx(2000.0)
    assert derived["contrast_ratio"] == pytest.approx(1.0)
    assert derived["ambient_ratio"] == pytest.approx(2850.0 / 850.0, rel=1e-3)


def test_derived_features_zero_and_near_zero_denominators() -> None:
    """Verify safe calculation of derived features when reference or ambient is zero or near zero."""
    ts = datetime.now(timezone.utc).isoformat()

    # Case 1: reference_value is 0.0 -> contrast_ratio must be 0.0, no ZeroDivisionError
    rec_zero_ref = SensorRecord(
        specimen_id="SEED-ZERO-REF",
        run_id="RUN-01",
        sample_LDR=2000.0,
        ambient_LDR=850.0,
        reference_value=0.0,
        sample_position="center",
        angle=45.0,
        LED_setting="WHITE_100PCT",
        timestamp=ts,
    )
    derived_zero_ref = rec_zero_ref.compute_standard_derived_features()
    assert derived_zero_ref["contrast_ratio"] == 0.0
    assert math.isfinite(derived_zero_ref["contrast_ratio"])

    # Case 2: reference_value is near-zero (1e-9) -> contrast_ratio must be 0.0, no float explosion
    rec_near_zero = SensorRecord(
        specimen_id="SEED-NEAR-ZERO",
        run_id="RUN-01",
        sample_LDR=2000.0,
        ambient_LDR=850.0,
        reference_value=1e-9,
        sample_position="center",
        angle=45.0,
        LED_setting="WHITE_100PCT",
        timestamp=ts,
    )
    derived_near = rec_near_zero.compute_standard_derived_features()
    assert derived_near["contrast_ratio"] == 0.0

    # Case 3: ambient_LDR is 0.0 -> ambient_ratio must be finite and bounded
    rec_zero_amb = SensorRecord(
        specimen_id="SEED-ZERO-AMB",
        run_id="RUN-01",
        sample_LDR=2000.0,
        ambient_LDR=0.0,
        reference_value=2400.0,
        sample_position="center",
        angle=45.0,
        LED_setting="WHITE_100PCT",
        timestamp=ts,
    )
    derived_zero_amb = rec_zero_amb.compute_standard_derived_features()
    assert math.isfinite(derived_zero_amb["ambient_ratio"])
    assert derived_zero_amb["ambient_ratio"] > 0.0


def test_voltage_conversion_helper() -> None:
    """Verify conversion of 12-bit ADC counts to physical 3.3V analog voltages."""
    ts = datetime.now(timezone.utc).isoformat()
    record = SensorRecord(
        specimen_id="SEED-VOLT",
        run_id="RUN-01",
        sample_LDR=4095.0,   # Full scale -> 3.3V
        ambient_LDR=2047.5,  # Half scale -> ~1.65V
        reference_value=0.0, # Zero scale -> 0.0V
        sample_position="center",
        angle=45.0,
        LED_setting="WHITE_100PCT",
        timestamp=ts,
    )
    v = record.to_voltages(vref=3.30)
    assert v["sample_voltage_V"] == pytest.approx(3.30, abs=0.01)
    assert v["ambient_voltage_V"] == pytest.approx(1.65, abs=0.01)
    assert v["reference_voltage_V"] == pytest.approx(0.00, abs=0.01)


def test_sensor_record_to_from_dict() -> None:
    """Verify lossless serialization and deserialization via dictionary."""
    ts = datetime.now(timezone.utc).isoformat()
    orig = SensorRecord(
        specimen_id="SEED-003",
        run_id="RUN-TEST-01",
        sample_LDR=1900.0,
        ambient_LDR=820.0,
        reference_value=2300.0,
        sample_position="slot_a",
        angle=30.0,
        LED_setting="WHITE_75PCT",
        timestamp=ts,
    )
    orig.compute_standard_derived_features()
    d = orig.to_dict()
    restored = SensorRecord.from_dict(d)
    assert restored.specimen_id == orig.specimen_id
    assert restored.sample_LDR == orig.sample_LDR
    assert restored.derived_features == orig.derived_features


def test_missing_fields_in_from_dict() -> None:
    """Verify that omitting required fields in dictionary raises MalformedMessageError."""
    incomplete = {
        "specimen_id": "SEED-001",
        "sample_LDR": 2000.0,
    }
    with pytest.raises(MalformedMessageError):
        SensorRecord.from_dict(incomplete)


@pytest.mark.parametrize("invalid_val", [float("nan"), float("inf"), float("-inf"), -1.0, 5000.0])
def test_invalid_adc_values(invalid_val: float) -> None:
    """Verify rejection of NaN, inf, negative, and out-of-range ADC counts."""
    ts = datetime.now(timezone.utc).isoformat()
    with pytest.raises(InvalidNumericValueError):
        SensorRecord(
            specimen_id="SEED-001",
            run_id="RUN-TEST-01",
            sample_LDR=invalid_val,
            ambient_LDR=850.0,
            reference_value=2400.0,
            sample_position="center",
            angle=45.0,
            LED_setting="WHITE_100PCT",
            timestamp=ts,
        )


def test_non_simulated_datasource_rejected() -> None:
    """Verify that claiming data is physically measured raises ValidationError."""
    ts = datetime.now(timezone.utc).isoformat()
    with pytest.raises(ValidationError):
        SensorRecord(
            specimen_id="SEED-001",
            run_id="RUN-TEST-01",
            sample_LDR=2000.0,
            ambient_LDR=850.0,
            reference_value=2400.0,
            sample_position="center",
            angle=45.0,
            LED_setting="WHITE_100PCT",
            timestamp=ts,
            data_source="physical_hardware_measured",  # Must be 'simulated'
        )


def test_timezone_aware_timestamp_handling() -> None:
    """Verify that timestamps with timezone offsets (+05:30, -04:00, Z) are accepted."""
    rec_ist = SensorRecord(
        specimen_id="SEED-IST",
        run_id="RUN-01",
        sample_LDR=2000.0,
        ambient_LDR=850.0,
        reference_value=2400.0,
        sample_position="center",
        angle=45.0,
        LED_setting="WHITE_100PCT",
        timestamp="2026-10-10T19:30:00+05:30",
    )
    assert rec_ist.timestamp == "2026-10-10T19:30:00+05:30"


def test_invalid_timestamp_rejected() -> None:
    """Verify that a malformed timestamp string is rejected."""
    with pytest.raises(MalformedMessageError):
        SensorRecord(
            specimen_id="SEED-001",
            run_id="RUN-TEST-01",
            sample_LDR=2000.0,
            ambient_LDR=850.0,
            reference_value=2400.0,
            sample_position="center",
            angle=45.0,
            LED_setting="WHITE_100PCT",
            timestamp="NOT_A_VALID_ISO_TIMESTAMP",
        )


def test_decision_request_json_lines() -> None:
    """Verify DecisionRequest JSON line serialization and parsing."""
    ts = datetime.now(timezone.utc).isoformat()
    req = DecisionRequest(
        request_id="REQ-JSON-01",
        features={"sample_LDR": 2100.0, "ambient_LDR": 850.0},
        timestamp=ts,
    )
    line = req.to_json_line()
    assert line.endswith("\n")

    restored = DecisionRequest.from_json_line(line)
    assert restored.request_id == "REQ-JSON-01"
    assert restored.features == req.features

    # Incomplete / corrupt JSON string
    with pytest.raises(MalformedMessageError):
        DecisionRequest.from_json_line('{"type":"measurement", "request_id":')


def test_decision_response_json_lines() -> None:
    """Verify DecisionResponse JSON line serialization and parsing."""
    ts = datetime.now(timezone.utc).isoformat()
    resp = DecisionResponse(
        request_id="REQ-RESP-01",
        label="BIN_B",
        confidence=0.92,
        timestamp=ts,
    )
    line = resp.to_json_line()
    assert line.endswith("\n")

    restored = DecisionResponse.from_json_line(line)
    assert restored.request_id == "REQ-RESP-01"
    assert restored.label == "BIN_B"
    assert restored.confidence == 0.92

    # Malformed JSON line
    with pytest.raises(MalformedMessageError):
        DecisionResponse.from_json_line("INVALID_JSON_LINE_RAW_TEXT")


def test_actuator_event_serialization() -> None:
    """Verify ActuatorEvent to/from dict."""
    ts = datetime.now(timezone.utc).isoformat()
    evt = ActuatorEvent(
        event_id="EVT-0001",
        timestamp=ts,
        request_id="REQ-001",
        decision="BIN_A",
        previous_angle_deg=90.0,
        target_angle_deg=45.0,
        resulting_angle_deg=45.0,
        status="EXECUTED",
        reason="Test execution",
        is_simulated=True,
    )
    d = evt.to_dict()
    restored = ActuatorEvent.from_dict(d)
    assert restored.event_id == evt.event_id
    assert restored.previous_angle_deg == 90.0
    assert restored.target_angle_deg == 45.0
    assert restored.resulting_angle_deg == 45.0
    assert restored.is_simulated is True
