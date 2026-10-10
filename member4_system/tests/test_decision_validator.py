"""
ReflectSort — Unit Tests for Decision Validator
Test Module: tests.test_decision_validator

Author: Ajitesh Karan (2500032236)
Course: Machine Learning – Embedded Systems Design (ML–ESD)
Team: ML-ESD-TEAM-117 (Project 12, Variant 06)
"""

import pytest
from datetime import datetime, timedelta, timezone

from reflectsort_member4.decision_validator import (
    DEFAULT_MAX_RESPONSE_LATENCY_SECONDS,
    DecisionValidator,
    DecisionValidatorConfig,
    ValidationResult,
)
from reflectsort_member4.schemas import DecisionResponse, SortingDecision


def test_valid_all_permitted_decisions() -> None:
    """Verify that all 5 permitted decisions pass validation when on-time and matched."""
    fixed_time = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)
    validator = DecisionValidator(
        config=DecisionValidatorConfig(max_response_latency_seconds=2.0),
        clock=lambda: fixed_time,
    )
    req_id = "REQ-100"
    req_ts = (fixed_time - timedelta(milliseconds=150)).isoformat()
    resp_ts = fixed_time.isoformat()

    for decision in SortingDecision:
        resp = DecisionResponse(
            request_id=req_id,
            label=decision.value,
            timestamp=resp_ts,
            confidence=0.92,
        )
        res = validator.validate(resp, expected_request_id=req_id, request_timestamp=req_ts)
        assert res.is_valid is True
        assert res.validated_action == decision
        assert res.error_code is None
        assert res.request_id == req_id
        validator.reset_session()


def test_timeout_exact_boundary_conditions() -> None:
    """
    Test exact timeout boundary conditions:
    - latency == 2.000s -> PASS (inclusive boundary <=)
    - latency == 1.999s -> PASS
    - latency == 2.001s -> FAIL (ERR_RESPONSE_EXPIRED)
    - latency == 0.000s -> PASS
    """
    fixed_now = datetime(2026, 10, 10, 12, 0, 10, tzinfo=timezone.utc)
    validator = DecisionValidator(
        config=DecisionValidatorConfig(max_response_latency_seconds=2.0),
        clock=lambda: fixed_now,
    )

    req_dt = datetime(2026, 10, 10, 12, 0, 8, tzinfo=timezone.utc)
    req_ts = req_dt.isoformat()

    # Case A: Exactly 2.000s (resp at 12:00:10.000) -> MUST PASS
    resp_exact = DecisionResponse(
        request_id="REQ-EXACT-2S",
        label="BIN_A",
        timestamp=(req_dt + timedelta(seconds=2.0)).isoformat(),
        confidence=0.95,
    )
    res_exact = validator.validate(resp_exact, expected_request_id="REQ-EXACT-2S", request_timestamp=req_ts)
    assert res_exact.is_valid is True
    assert res_exact.error_code is None

    # Case B: 1.999s -> MUST PASS
    resp_within = DecisionResponse(
        request_id="REQ-WITHIN-2S",
        label="BIN_A",
        timestamp=(req_dt + timedelta(seconds=1.999)).isoformat(),
        confidence=0.95,
    )
    res_within = validator.validate(resp_within, expected_request_id="REQ-WITHIN-2S", request_timestamp=req_ts)
    assert res_within.is_valid is True

    # Case C: 2.001s (just 1ms past deadline) -> MUST FAIL with ERR_RESPONSE_EXPIRED
    resp_over = DecisionResponse(
        request_id="REQ-OVER-2S",
        label="BIN_A",
        timestamp=(req_dt + timedelta(seconds=2.001)).isoformat(),
        confidence=0.95,
    )
    res_over = validator.validate(resp_over, expected_request_id="REQ-OVER-2S", request_timestamp=req_ts)
    assert res_over.is_valid is False
    assert res_over.validated_action == SortingDecision.HOLD
    assert res_over.error_code == "ERR_RESPONSE_EXPIRED"

    # Case D: 0.000s -> MUST PASS
    resp_zero = DecisionResponse(
        request_id="REQ-ZERO-LATENCY",
        label="BIN_A",
        timestamp=req_ts,
        confidence=0.95,
    )
    res_zero = validator.validate(resp_zero, expected_request_id="REQ-ZERO-LATENCY", request_timestamp=req_ts)
    assert res_zero.is_valid is True


def test_future_dated_response_rejection() -> None:
    """Verify that response timestamps in the future beyond acceptable clock drift are rejected."""
    fixed_now = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)
    validator = DecisionValidator(
        config=DecisionValidatorConfig(max_future_clock_drift_seconds=0.50),
        clock=lambda: fixed_now,
    )

    req_ts = (fixed_now - timedelta(seconds=0.1)).isoformat()
    # Response claims to be 5 seconds in future relative to current clock
    future_resp_ts = (fixed_now + timedelta(seconds=5.0)).isoformat()

    resp = DecisionResponse(
        request_id="REQ-FUTURE",
        label="BIN_A",
        timestamp=future_resp_ts,
        confidence=0.95,
    )
    res = validator.validate(resp, expected_request_id="REQ-FUTURE", request_timestamp=req_ts)
    assert res.is_valid is False
    assert res.validated_action == SortingDecision.HOLD
    assert res.error_code == "ERR_FUTURE_DATED_TIMESTAMP"
    assert "future-dated" in res.reason.lower()


def test_timezone_offset_handling_utc_vs_ist() -> None:
    """Verify that timestamps with non-UTC timezone offsets compare correctly without skew."""
    # Request in UTC, Response in IST (+05:30) representing 100ms later
    req_dt_utc = datetime(2026, 10, 10, 12, 0, 0, 0, tzinfo=timezone.utc)
    resp_dt_ist = datetime(2026, 10, 10, 17, 30, 0, 100000, tzinfo=timezone(timedelta(hours=5, minutes=30)))

    now_clock = req_dt_utc + timedelta(milliseconds=150)
    validator = DecisionValidator(
        config=DecisionValidatorConfig(max_response_latency_seconds=2.0),
        clock=lambda: now_clock,
    )

    resp = DecisionResponse(
        request_id="REQ-TZ",
        label="BIN_B",
        timestamp=resp_dt_ist.isoformat(),
        confidence=0.90,
    )
    res = validator.validate(resp, expected_request_id="REQ-TZ", request_timestamp=req_dt_utc.isoformat())
    assert res.is_valid is True
    assert res.latency_seconds == pytest.approx(0.100, abs=0.001)


def test_confidence_threshold_and_policies() -> None:
    """
    Test confidence gating:
    - confidence == threshold (boundary -> PASS)
    - confidence < threshold (FAIL)
    - confidence > threshold (PASS)
    - require_confidence = True with missing confidence (FAIL)
    - require_confidence = False with missing confidence (PASS)
    """
    fixed_now = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)
    validator = DecisionValidator(
        config=DecisionValidatorConfig(
            min_confidence_threshold=0.85,
            require_confidence=False,
        ),
        clock=lambda: fixed_now,
    )
    req_ts = (fixed_now - timedelta(milliseconds=50)).isoformat()

    # 1. Exact boundary: confidence == 0.85 -> PASS
    res_exact = validator.validate(
        DecisionResponse(request_id="R-EXACT", label="BIN_A", timestamp=fixed_now.isoformat(), confidence=0.85),
        expected_request_id="R-EXACT",
        request_timestamp=req_ts,
    )
    assert res_exact.is_valid is True

    # 2. Below threshold: confidence 0.849 -> FAIL
    res_below = validator.validate(
        DecisionResponse(request_id="R-BELOW", label="BIN_A", timestamp=fixed_now.isoformat(), confidence=0.849),
        expected_request_id="R-BELOW",
        request_timestamp=req_ts,
    )
    assert res_below.is_valid is False
    assert res_below.error_code == "ERR_LOW_CONFIDENCE"

    # 3. Missing confidence with require_confidence=False -> PASS
    res_missing_ok = validator.validate(
        DecisionResponse(request_id="R-NO-CONF", label="BIN_A", timestamp=fixed_now.isoformat(), confidence=None),
        expected_request_id="R-NO-CONF",
        request_timestamp=req_ts,
    )
    assert res_missing_ok.is_valid is True

    # 4. Missing confidence with require_confidence=True -> FAIL (ERR_MISSING_CONFIDENCE)
    validator_strict = DecisionValidator(
        config=DecisionValidatorConfig(require_confidence=True),
        clock=lambda: fixed_now,
    )
    res_strict_missing = validator_strict.validate(
        DecisionResponse(request_id="R-STRICT-MISSING", label="BIN_A", timestamp=fixed_now.isoformat(), confidence=None),
        expected_request_id="R-STRICT-MISSING",
        request_timestamp=req_ts,
    )
    assert res_strict_missing.is_valid is False
    assert res_strict_missing.error_code == "ERR_MISSING_CONFIDENCE"


def test_replay_protection_blocks_duplicate_responses() -> None:
    """Verify that replaying a response with an already processed request_id is rejected."""
    fixed_now = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)
    validator = DecisionValidator(
        config=DecisionValidatorConfig(enable_replay_protection=True),
        clock=lambda: fixed_now,
    )
    req_id = "REQ-ONCE-01"
    req_ts = (fixed_now - timedelta(milliseconds=50)).isoformat()
    resp = DecisionResponse(request_id=req_id, label="BIN_A", timestamp=fixed_now.isoformat(), confidence=0.95)

    # First attempt -> MUST PASS
    res1 = validator.validate(resp, expected_request_id=req_id, request_timestamp=req_ts)
    assert res1.is_valid is True

    # Replay attempt with same ID -> MUST FAIL (ERR_DUPLICATE_RESPONSE)
    res2 = validator.validate(resp, expected_request_id=req_id, request_timestamp=req_ts)
    assert res2.is_valid is False
    assert res2.error_code == "ERR_DUPLICATE_RESPONSE"

    # After session reset -> MUST PASS
    validator.reset_session()
    res3 = validator.validate(resp, expected_request_id=req_id, request_timestamp=req_ts)
    assert res3.is_valid is True


def test_raw_json_string_and_corrupt_payload_handling() -> None:
    """Verify handling of raw JSON strings and malformed payload formats."""
    fixed_now = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)
    validator = DecisionValidator(clock=lambda: fixed_now)

    # Valid JSON string
    json_str = f'{{"type":"decision","request_id":"REQ-RAW","label":"BIN_C","timestamp":"{fixed_now.isoformat()}"}}'
    res = validator.validate(json_str, expected_request_id="REQ-RAW")
    assert res.is_valid is True
    assert res.validated_action == SortingDecision.BIN_C

    # Incomplete / corrupt JSON string
    corrupt_json = '{"type":"decision", "request_id":'
    res_corrupt = validator.validate(corrupt_json, expected_request_id="REQ-RAW")
    assert res_corrupt.is_valid is False
    assert res_corrupt.validated_action == SortingDecision.HOLD
    assert res_corrupt.error_code == "ERR_MALFORMED_JSON"


def test_request_id_mismatch_rejected() -> None:
    """Verify that a response with an unexpected request_id is rejected and defaults to HOLD."""
    fixed_time = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)
    validator = DecisionValidator(clock=lambda: fixed_time)

    resp = DecisionResponse(
        request_id="WRONG_ID_999",
        label="BIN_A",
        timestamp=fixed_time.isoformat(),
        confidence=0.95,
    )
    res = validator.validate(resp, expected_request_id="ACTIVE_REQ_001")
    assert res.is_valid is False
    assert res.validated_action == SortingDecision.HOLD
    assert res.error_code == "ERR_REQUEST_ID_MISMATCH"


def test_predated_response_rejected() -> None:
    """Verify that response timestamp predating request timestamp is rejected (clock skew anomaly)."""
    fixed_now = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)
    validator = DecisionValidator(clock=lambda: fixed_now)

    req_ts = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc).isoformat()
    resp_ts = datetime(2026, 10, 10, 11, 59, 50, tzinfo=timezone.utc).isoformat()

    resp = DecisionResponse(
        request_id="REQ-SKEW",
        label="BIN_A",
        timestamp=resp_ts,
        confidence=0.95,
    )
    res = validator.validate(resp, expected_request_id="REQ-SKEW", request_timestamp=req_ts)
    assert res.is_valid is False
    assert res.validated_action == SortingDecision.HOLD
    assert res.error_code == "ERR_CLOCK_SKEW_PREDATED"


def test_distinguish_accepted_hold_from_rejected_hold() -> None:
    """Verify clear distinction in logs between intentional HOLD and fallback HOLD."""
    fixed_now = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)
    validator = DecisionValidator(clock=lambda: fixed_now)

    # 1. Accepted HOLD
    resp_hold = DecisionResponse(
        request_id="REQ-HOLD",
        label="HOLD",
        timestamp=fixed_now.isoformat(),
    )
    res_accepted = validator.validate(resp_hold, expected_request_id="REQ-HOLD")
    assert res_accepted.is_valid is True
    assert res_accepted.validated_action == SortingDecision.HOLD
    assert res_accepted.error_code is None

    # 2. Rejected Malformed
    res_rejected = validator.validate({"request_id": "REQ-HOLD-2"}, expected_request_id="REQ-HOLD-2")
    assert res_rejected.is_valid is False
    assert res_rejected.validated_action == SortingDecision.HOLD
    assert res_rejected.error_code is not None
