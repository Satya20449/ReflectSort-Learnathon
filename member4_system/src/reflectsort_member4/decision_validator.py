"""
ReflectSort — Decision Validator Module
Module: reflectsort_member4.decision_validator

Enforces the safety-critical validation logic required before any actuator action
can be commanded or simulated on the sorting mechanism.

Safety Invariants Enforced:
1. Message Schema Integrity: Verifies payload formatting, types, and required keys.
2. Request ID Correlation: Ensures the response matches the active pending request.
3. Bounded Replay Protection: Rejects duplicate/replayed responses using an LRU/FIFO sliding history.
4. Temporal Freshness / Expiry: Rejects stale responses exceeding latency threshold (<= max_latency).
5. Monotonic Time: Rejects predated responses (resp < req) and future-dated responses (resp > now + drift).
6. Permitted Outcome Whitelist: Restricts labels strictly to {BIN_A, BIN_B, BIN_C, REJECT_UNKNOWN, HOLD}.
7. Confidence Gating: Enforces configurable confidence thresholds and explicit confidence policies.
8. Failsafe Default: On ANY validation error, strictly defaults to HOLD with auditable error codes.

Author: Ajitesh Karan (2500032236)
Course: Machine Learning – Embedded Systems Design (ML–ESD)
Team: ML-ESD-TEAM-117 (Project 12, Variant 06)
"""

from __future__ import annotations

import json
import math
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, Set, Union

from reflectsort_member4.schemas import (
    DecisionResponse,
    InvalidNumericValueError,
    MalformedMessageError,
    SortingDecision,
    ValidationError,
)

# Default timing & policy constants
DEFAULT_MAX_RESPONSE_LATENCY_SECONDS: float = 2.0
DEFAULT_MAX_FUTURE_DRIFT_SECONDS: float = 0.50
DEFAULT_MAX_TRACKED_REQUEST_HISTORY: int = 10000


@dataclass
class DecisionValidatorConfig:
    """
    Configuration policy for the decision validator.
    """
    allowed_labels: Set[str] = field(
        default_factory=lambda: {
            SortingDecision.BIN_A.value,
            SortingDecision.BIN_B.value,
            SortingDecision.BIN_C.value,
            SortingDecision.REJECT_UNKNOWN.value,
            SortingDecision.HOLD.value,
        }
    )
    max_response_latency_seconds: float = DEFAULT_MAX_RESPONSE_LATENCY_SECONDS
    max_future_clock_drift_seconds: float = DEFAULT_MAX_FUTURE_DRIFT_SECONDS
    min_confidence_threshold: float = 0.0       # Configurable threshold (0.0 = inactive)
    require_confidence: bool = False            # If True, missing confidence score is rejected
    enforce_request_id_match: bool = True
    enforce_timestamp_freshness: bool = True
    enable_replay_protection: bool = True       # Rejects duplicate/replayed responses
    max_replay_history_size: int = DEFAULT_MAX_TRACKED_REQUEST_HISTORY

    def validate(self) -> None:
        if self.max_response_latency_seconds <= 0:
            raise ValidationError("max_response_latency_seconds must be positive (> 0)")
        if self.max_future_clock_drift_seconds < 0:
            raise ValidationError("max_future_clock_drift_seconds cannot be negative")
        if not (0.0 <= self.min_confidence_threshold <= 1.0):
            raise ValidationError("min_confidence_threshold must be within [0.0, 1.0]")
        if self.max_replay_history_size <= 0:
            raise ValidationError("max_replay_history_size must be positive (> 0)")


@dataclass
class ValidationResult:
    """
    Structured outcome of the decision validation process.
    """
    is_valid: bool
    validated_action: SortingDecision
    request_id: str
    reason: str
    error_code: Optional[str] = None
    evaluated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    original_label: Optional[str] = None
    confidence: Optional[float] = None
    latency_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "validated_action": self.validated_action.value,
            "request_id": self.request_id,
            "reason": self.reason,
            "error_code": self.error_code,
            "evaluated_at": self.evaluated_at,
            "original_label": self.original_label,
            "confidence": self.confidence,
            "latency_seconds": self.latency_seconds,
        }


class DecisionValidator:
    """
    Validates classification responses received from the ML/Host layer.
    Guarantees deterministic safety enforcement and failsafe fallback to HOLD.
    """

    def __init__(
        self,
        config: Optional[DecisionValidatorConfig] = None,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        """
        Initialize the validator.

        Args:
            config: Validator configuration policy
            clock: Optional injectable time provider for deterministic testing
        """
        self.config = config or DecisionValidatorConfig()
        self._clock: Callable[[], datetime] = clock or (lambda: datetime.now(timezone.utc))
        # Bounded FIFO/LRU dictionary mapping request_id -> processed_timestamp
        self._processed_request_history: OrderedDict[str, float] = OrderedDict()

    @property
    def clock(self) -> Callable[[], datetime]:
        """Return the current clock callable."""
        return self._clock

    @clock.setter
    def clock(self, clock_fn: Callable[[], datetime]) -> None:
        """Inject a custom clock callable for deterministic testing."""
        self._clock = clock_fn

    def reset_session(self) -> None:
        """Clear session memory (e.g. replay history cache)."""
        self._processed_request_history.clear()

    def get_processed_history_count(self) -> int:
        """Return the number of currently tracked request IDs in replay protection history."""
        return len(self._processed_request_history)

    def _parse_timestamp_to_utc(self, ts_input: Union[str, datetime]) -> datetime:
        """Parse ISO 8601 string or datetime object and return UTC datetime."""
        if isinstance(ts_input, datetime):
            if ts_input.tzinfo is None:
                return ts_input.replace(tzinfo=timezone.utc)
            return ts_input.astimezone(timezone.utc)
        if not isinstance(ts_input, str) or not ts_input.strip():
            raise MalformedMessageError(f"Invalid timestamp string: {ts_input!r}")
        ts_str = ts_input.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt

    def validate(
        self,
        response: Union[DecisionResponse, Dict[str, Any], str],
        expected_request_id: str,
        request_timestamp: Optional[Union[str, datetime]] = None,
    ) -> ValidationResult:
        """
        Validate an incoming decision response against safety rules and active context.

        Args:
            response: DecisionResponse instance, dictionary, or raw JSON string
            expected_request_id: Identifier of the pending measurement request
            request_timestamp: Timestamp when the measurement request was dispatched

        Returns:
            ValidationResult with validated_action (strictly defaults to HOLD on any failure)
        """
        now = self._clock()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        else:
            now = now.astimezone(timezone.utc)
        eval_time_str = now.isoformat()

        # Step 1: Parse and schema-validate the response object
        resp_obj: DecisionResponse
        if isinstance(response, str):
            try:
                data = json.loads(response.strip())
                resp_obj = DecisionResponse.from_dict(data)
            except Exception as e:
                return ValidationResult(
                    is_valid=False,
                    validated_action=SortingDecision.HOLD,
                    request_id=expected_request_id,
                    reason=f"Malformed raw JSON line for DecisionResponse: {e}",
                    error_code="ERR_MALFORMED_JSON",
                    evaluated_at=eval_time_str,
                )
        elif isinstance(response, DecisionResponse):
            resp_obj = response
            try:
                resp_obj.validate()
            except Exception as e:
                return ValidationResult(
                    is_valid=False,
                    validated_action=SortingDecision.HOLD,
                    request_id=getattr(resp_obj, "request_id", expected_request_id),
                    reason=f"Schema validation failed on DecisionResponse: {e}",
                    error_code="ERR_SCHEMA_INVALID",
                    evaluated_at=eval_time_str,
                )
        elif isinstance(response, dict):
            try:
                resp_obj = DecisionResponse.from_dict(response)
            except Exception as e:
                req_id = response.get("request_id", expected_request_id) if isinstance(response, dict) else expected_request_id
                return ValidationResult(
                    is_valid=False,
                    validated_action=SortingDecision.HOLD,
                    request_id=str(req_id),
                    reason=f"Malformed dictionary message for DecisionResponse: {e}",
                    error_code="ERR_MALFORMED_MESSAGE",
                    evaluated_at=eval_time_str,
                )
        else:
            return ValidationResult(
                is_valid=False,
                validated_action=SortingDecision.HOLD,
                request_id=expected_request_id,
                reason=f"Unsupported response payload type: {type(response).__name__}",
                error_code="ERR_UNSUPPORTED_TYPE",
                evaluated_at=eval_time_str,
            )

        req_id = resp_obj.request_id
        label = resp_obj.label
        confidence = resp_obj.confidence

        # Step 2: Request ID Correlation Check
        if self.config.enforce_request_id_match:
            if req_id != expected_request_id:
                return ValidationResult(
                    is_valid=False,
                    validated_action=SortingDecision.HOLD,
                    request_id=req_id,
                    reason=f"Request ID mismatch: received '{req_id}', expected '{expected_request_id}'",
                    error_code="ERR_REQUEST_ID_MISMATCH",
                    evaluated_at=eval_time_str,
                    original_label=label,
                    confidence=confidence,
                )

        # Step 3: Replay / Duplicate Response Protection Check (Bounded History)
        if self.config.enable_replay_protection:
            if req_id in self._processed_request_history:
                return ValidationResult(
                    is_valid=False,
                    validated_action=SortingDecision.HOLD,
                    request_id=req_id,
                    reason=f"Duplicate / replayed response detected for already processed request_id '{req_id}'",
                    error_code="ERR_DUPLICATE_RESPONSE",
                    evaluated_at=eval_time_str,
                    original_label=label,
                    confidence=confidence,
                )

        # Step 4: Parse and validate response timestamp
        try:
            resp_dt = self._parse_timestamp_to_utc(resp_obj.timestamp)
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                validated_action=SortingDecision.HOLD,
                request_id=req_id,
                reason=f"Invalid response timestamp format '{resp_obj.timestamp}': {e}",
                error_code="ERR_INVALID_TIMESTAMP",
                evaluated_at=eval_time_str,
                original_label=label,
                confidence=confidence,
            )

        # Step 5: Temporal Monotonicity & Freshness Checks
        latency: Optional[float] = None
        if self.config.enforce_timestamp_freshness:
            # Future-dated check (against current clock + drift allowance)
            future_drift = (resp_dt - now).total_seconds()
            if future_drift > self.config.max_future_clock_drift_seconds:
                return ValidationResult(
                    is_valid=False,
                    validated_action=SortingDecision.HOLD,
                    request_id=req_id,
                    reason=f"Temporal violation: response timestamp is future-dated by {future_drift:.3f}s (max drift: {self.config.max_future_clock_drift_seconds}s)",
                    error_code="ERR_FUTURE_DATED_TIMESTAMP",
                    evaluated_at=eval_time_str,
                    original_label=label,
                    confidence=confidence,
                    latency_seconds=future_drift,
                )

            # Latency relative to request timestamp if provided, else relative to current time
            if request_timestamp is not None:
                try:
                    req_dt = self._parse_timestamp_to_utc(request_timestamp)
                    req_future_drift = (req_dt - now).total_seconds()
                    if req_future_drift > self.config.max_future_clock_drift_seconds:
                        return ValidationResult(
                            is_valid=False,
                            validated_action=SortingDecision.HOLD,
                            request_id=req_id,
                            reason=f"Temporal violation: request timestamp is future-dated by {req_future_drift:.3f}s (max drift: {self.config.max_future_clock_drift_seconds}s)",
                            error_code="ERR_FUTURE_DATED_TIMESTAMP",
                            evaluated_at=eval_time_str,
                            original_label=label,
                            confidence=confidence,
                            latency_seconds=req_future_drift,
                        )

                    resp_latency = (resp_dt - req_dt).total_seconds()
                    if resp_latency < 0:
                        return ValidationResult(
                            is_valid=False,
                            validated_action=SortingDecision.HOLD,
                            request_id=req_id,
                            reason=f"Temporal violation: response timestamp predates request timestamp ({resp_latency:.3f}s)",
                            error_code="ERR_CLOCK_SKEW_PREDATED",
                            evaluated_at=eval_time_str,
                            original_label=label,
                            confidence=confidence,
                            latency_seconds=resp_latency,
                        )
                    elapsed_since_request = (now - req_dt).total_seconds()
                    latency = max(resp_latency, elapsed_since_request)
                except Exception as e:
                    return ValidationResult(
                        is_valid=False,
                        validated_action=SortingDecision.HOLD,
                        request_id=req_id,
                        reason=f"Invalid request timestamp: {e}",
                        error_code="ERR_INVALID_REQUEST_TIMESTAMP",
                        evaluated_at=eval_time_str,
                        original_label=label,
                    )
            else:
                latency = abs((now - resp_dt).total_seconds())

            # Expiry boundary condition: latency > max_response_latency_seconds fails
            if latency is not None and latency > self.config.max_response_latency_seconds:
                return ValidationResult(
                    is_valid=False,
                    validated_action=SortingDecision.HOLD,
                    request_id=req_id,
                    reason=f"Decision response expired: latency {latency:.3f}s exceeds limit {self.config.max_response_latency_seconds:.3f}s",
                    error_code="ERR_RESPONSE_EXPIRED",
                    evaluated_at=eval_time_str,
                    original_label=label,
                    confidence=confidence,
                    latency_seconds=latency,
                )

        # Step 6: Permitted Label Whitelist Check
        if label not in self.config.allowed_labels:
            return ValidationResult(
                is_valid=False,
                validated_action=SortingDecision.HOLD,
                request_id=req_id,
                reason=f"Unsupported decision label '{label}'. Allowed whitelist: {sorted(list(self.config.allowed_labels))}",
                error_code="ERR_UNSUPPORTED_LABEL",
                evaluated_at=eval_time_str,
                original_label=label,
                confidence=confidence,
                latency_seconds=latency,
            )

        # Step 7: Confidence Threshold & Policy Check
        if self.config.require_confidence and confidence is None:
            return ValidationResult(
                is_valid=False,
                validated_action=SortingDecision.HOLD,
                request_id=req_id,
                reason="Policy violation: confidence score is required by validator configuration but was omitted",
                error_code="ERR_MISSING_CONFIDENCE",
                evaluated_at=eval_time_str,
                original_label=label,
                latency_seconds=latency,
            )

        if confidence is not None:
            if confidence < self.config.min_confidence_threshold:
                return ValidationResult(
                    is_valid=False,
                    validated_action=SortingDecision.HOLD,
                    request_id=req_id,
                    reason=f"Inference confidence {confidence:.3f} is below minimum threshold {self.config.min_confidence_threshold:.3f}",
                    error_code="ERR_LOW_CONFIDENCE",
                    evaluated_at=eval_time_str,
                    original_label=label,
                    confidence=confidence,
                    latency_seconds=latency,
                )

        # Step 8: Decision successfully validated
        target_decision = SortingDecision(label)

        # Record into replay protection bounded cache (FIFO eviction of oldest single item)
        if self.config.enable_replay_protection:
            while len(self._processed_request_history) >= self.config.max_replay_history_size:
                self._processed_request_history.popitem(last=False)
            self._processed_request_history[req_id] = now.timestamp()

        return ValidationResult(
            is_valid=True,
            validated_action=target_decision,
            request_id=req_id,
            reason=f"Decision '{target_decision.value}' successfully verified and permitted",
            error_code=None,
            evaluated_at=eval_time_str,
            original_label=label,
            confidence=confidence,
            latency_seconds=latency,
        )
