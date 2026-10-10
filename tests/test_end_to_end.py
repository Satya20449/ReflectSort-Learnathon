"""
ReflectSort — End-to-End System Integration Tests
Course: Machine Learning – Embedded Systems Design (ML-ESD)
Team: ML-ESD-TEAM-117 | Project ID: PROJECT-12-VARIANT-06

Tests the complete integrated pipeline:
SensorSimulator (M4) -> Feature Extraction -> ML Model Inference (M2) ->
DecisionValidator Safety Gate (M4) -> ActuatorSimulator Diverter (M4) -> Audit Logging (M3)
"""

from __future__ import annotations

import datetime as dt
import unittest
from pathlib import Path

from application.shade_demo import Predictor
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


class TestEndToEndPipeline(unittest.TestCase):
    """Integration test of the complete ReflectSort pipeline."""

    def setUp(self):
        self.sensor_sim = SensorSimulator(SensorSimulatorConfig(random_seed=117, noise_std_dev=5.0))
        self.predictor = Predictor()
        self.validator = DecisionValidator(DecisionValidatorConfig(
            max_response_latency_seconds=2.0,
            min_confidence_threshold=0.60,
            require_confidence=True,
        ))
        self.actuator = ActuatorSimulator(ActuatorConfig(
            diverter_mode="THREE_BIN",
            home_angle_deg=90.0,
            reject_action_behavior="RETURN_TO_HOME",
        ))

    def test_nominal_dark_specimen_flow(self):
        """Dark shade grain must classify as BIN_A, pass safety gate, and actuate to 45.0 degrees."""
        req_ts = dt.datetime.now(dt.timezone.utc).isoformat()
        record = self.sensor_sim.generate_reading(
            specimen_id="GRAIN-DARK-01",
            run_id="TEST-RUN",
            profile_name="SIM_DARK",
            timestamp=req_ts,
        )

        feats = record.to_approved_ml_features()
        action, conf, note = self.predictor.predict(feats["sample_LDR"], feats["ambient_LDR"], record.reference_value)
        self.assertEqual(action, "BIN_A")
        self.assertGreaterEqual(conf, 0.60)

        resp_ts = dt.datetime.now(dt.timezone.utc).isoformat()
        response = DecisionResponse(
            request_id="REQ-DARK-01",
            label=action,
            confidence=conf,
            timestamp=resp_ts,
        )

        val_result = self.validator.validate(
            response=response,
            expected_request_id="REQ-DARK-01",
            request_timestamp=record.timestamp,
        )
        self.assertTrue(val_result.is_valid)
        self.assertEqual(val_result.validated_action, SortingDecision.BIN_A)

        act_evt = self.actuator.execute_decision(val_result)
        self.assertEqual(act_evt.status, "EXECUTED")
        self.assertEqual(act_evt.resulting_angle_deg, 45.0)
        self.assertEqual(self.actuator.current_state, "DIVERT_BIN_A")

    def test_nominal_medium_specimen_flow(self):
        """Medium shade grain must classify as BIN_B, pass safety gate, and actuate to 90.0 degrees."""
        req_ts = dt.datetime.now(dt.timezone.utc).isoformat()
        record = self.sensor_sim.generate_reading(
            specimen_id="GRAIN-MED-01",
            run_id="TEST-RUN",
            profile_name="SIM_MEDIUM",
            timestamp=req_ts,
        )

        feats = record.to_approved_ml_features()
        action, conf, note = self.predictor.predict(feats["sample_LDR"], feats["ambient_LDR"], record.reference_value)
        self.assertEqual(action, "BIN_B")

        response = DecisionResponse(
            request_id="REQ-MED-01",
            label=action,
            confidence=conf,
            timestamp=dt.datetime.now(dt.timezone.utc).isoformat(),
        )

        val_result = self.validator.validate(
            response=response,
            expected_request_id="REQ-MED-01",
            request_timestamp=record.timestamp,
        )
        self.assertTrue(val_result.is_valid)
        self.assertEqual(val_result.validated_action, SortingDecision.BIN_B)

        act_evt = self.actuator.execute_decision(val_result)
        self.assertEqual(act_evt.status, "EXECUTED")
        self.assertEqual(act_evt.resulting_angle_deg, 90.0)
        self.assertEqual(self.actuator.current_state, "DIVERT_BIN_B")

    def test_nominal_light_specimen_flow(self):
        """Light shade grain must classify as BIN_C, pass safety gate, and actuate to 135.0 degrees."""
        req_ts = dt.datetime.now(dt.timezone.utc).isoformat()
        record = self.sensor_sim.generate_reading(
            specimen_id="GRAIN-LIGHT-01",
            run_id="TEST-RUN",
            profile_name="SIM_LIGHT",
            timestamp=req_ts,
        )

        feats = record.to_approved_ml_features()
        action, conf, note = self.predictor.predict(feats["sample_LDR"], feats["ambient_LDR"], record.reference_value)
        self.assertEqual(action, "BIN_C")

        response = DecisionResponse(
            request_id="REQ-LIGHT-01",
            label=action,
            confidence=conf,
            timestamp=dt.datetime.now(dt.timezone.utc).isoformat(),
        )

        val_result = self.validator.validate(
            response=response,
            expected_request_id="REQ-LIGHT-01",
            request_timestamp=record.timestamp,
        )
        self.assertTrue(val_result.is_valid)
        self.assertEqual(val_result.validated_action, SortingDecision.BIN_C)

        act_evt = self.actuator.execute_decision(val_result)
        self.assertEqual(act_evt.status, "EXECUTED")
        self.assertEqual(act_evt.resulting_angle_deg, 135.0)
        self.assertEqual(self.actuator.current_state, "DIVERT_BIN_C")


class TestSafetyGateEnforcement(unittest.TestCase):
    """Test safety gating, replay protection, timeouts, and actuator fail-safe behavior."""

    def setUp(self):
        self.validator = DecisionValidator(DecisionValidatorConfig(
            max_response_latency_seconds=2.0,
            max_future_clock_drift_seconds=0.5,
            min_confidence_threshold=0.60,
        ))
        self.actuator = ActuatorSimulator(ActuatorConfig(
            diverter_mode="THREE_BIN",
            home_angle_deg=90.0,
            reject_action_behavior="RETURN_TO_HOME",
        ))

    def test_response_timeout_triggers_hold_and_safe_home(self):
        """A response with latency > 2.0s must be rejected and safely home the actuator."""
        now = dt.datetime.now(dt.timezone.utc)
        req_ts = (now - dt.timedelta(seconds=2.85)).isoformat()
        resp_ts = now.isoformat()

        response = DecisionResponse(
            request_id="REQ-STALE-01",
            label="BIN_A",
            confidence=0.95,
            timestamp=resp_ts,
        )

        val_result = self.validator.validate(
            response=response,
            expected_request_id="REQ-STALE-01",
            request_timestamp=req_ts,
        )

        self.assertFalse(val_result.is_valid)
        self.assertEqual(val_result.validated_action, SortingDecision.HOLD)
        self.assertEqual(val_result.error_code, "ERR_RESPONSE_EXPIRED")

        act_evt = self.actuator.execute_decision(val_result)
        self.assertEqual(act_evt.status, "REJECTED")
        self.assertEqual(act_evt.resulting_angle_deg, 90.0)
        self.assertEqual(self.actuator.current_state, "SAFETY_BLOCKED_HOME")

    def test_duplicate_response_blocked_by_replay_protection(self):
        """Replaying a previously accepted response must be blocked."""
        now = dt.datetime.now(dt.timezone.utc)
        req_ts = (now - dt.timedelta(seconds=0.10)).isoformat()
        resp_ts = now.isoformat()

        response = DecisionResponse(
            request_id="REQ-DUP-01",
            label="BIN_B",
            confidence=0.92,
            timestamp=resp_ts,
        )

        # First validation: Success
        res1 = self.validator.validate(response=response, expected_request_id="REQ-DUP-01", request_timestamp=req_ts)
        self.assertTrue(res1.is_valid)

        # Duplicate replay attempt: Blocked
        res2 = self.validator.validate(response=response, expected_request_id="REQ-DUP-01", request_timestamp=req_ts)
        self.assertFalse(res2.is_valid)
        self.assertEqual(res2.validated_action, SortingDecision.HOLD)
        self.assertEqual(res2.error_code, "ERR_DUPLICATE_RESPONSE")

    def test_mismatched_request_id_blocked(self):
        """Mismatched request IDs must fail validation immediately."""
        now_ts = dt.datetime.now(dt.timezone.utc).isoformat()
        response = DecisionResponse(
            request_id="REQ-WRONG-999",
            label="BIN_A",
            confidence=0.90,
            timestamp=now_ts,
        )

        val_result = self.validator.validate(
            response=response,
            expected_request_id="REQ-EXPECTED-01",
            request_timestamp=now_ts,
        )
        self.assertFalse(val_result.is_valid)
        self.assertEqual(val_result.error_code, "ERR_REQUEST_ID_MISMATCH")

    def test_future_dated_timestamp_blocked(self):
        """Future-dated responses exceeding drift tolerance (0.5s) must be rejected."""
        now = dt.datetime.now(dt.timezone.utc)
        req_ts = now.isoformat()
        future_resp_ts = (now + dt.timedelta(seconds=2.0)).isoformat()

        response = DecisionResponse(
            request_id="REQ-FUTURE-01",
            label="BIN_C",
            confidence=0.95,
            timestamp=future_resp_ts,
        )

        val_result = self.validator.validate(
            response=response,
            expected_request_id="REQ-FUTURE-01",
            request_timestamp=req_ts,
        )
        self.assertFalse(val_result.is_valid)
        self.assertEqual(val_result.error_code, "ERR_FUTURE_DATED_TIMESTAMP")

    def test_unsupported_decision_label_blocked(self):
        """Labels not in allowed whitelist must be rejected."""
        now_ts = dt.datetime.now(dt.timezone.utc).isoformat()
        raw_dict = {
            "type": "decision",
            "request_id": "REQ-UNSUPPORTED-01",
            "label": "BIN_INVALID_LABEL",
            "confidence": 0.90,
            "timestamp": now_ts,
        }
        val_result = self.validator.validate(
            response=raw_dict,
            expected_request_id="REQ-UNSUPPORTED-01",
            request_timestamp=now_ts,
        )
        self.assertFalse(val_result.is_valid)
        self.assertIn(val_result.error_code, ["ERR_MALFORMED_MESSAGE", "ERR_UNSUPPORTED_LABEL", "ERR_SCHEMA_INVALID"])


if __name__ == "__main__":
    unittest.main()
