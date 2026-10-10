"""
ReflectSort — Shared Data Schemas & Validation Rules
Module: reflectsort_member4.schemas

Defines the common data structures, message types, and strict validation rules
for the ReflectSort hardware-simulation interface, decision exchange, and actuator execution.

Author: Ajitesh Karan (2500032236)
Course: Machine Learning – Embedded Systems Design (ML–ESD)
Team: ML-ESD-TEAM-117 (Project 12, Variant 06)
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

# Hardware standard ADC resolution constants (STM32F446RE 12-bit ADC)
DEFAULT_ADC_RESOLUTION_BITS: int = 12
DEFAULT_MAX_ADC_COUNT: float = float((1 << DEFAULT_ADC_RESOLUTION_BITS) - 1)  # 4095.0
DEFAULT_MIN_ADC_COUNT: float = 0.0
DEFAULT_ADC_VREF_VOLTS: float = 3.30
NUMERICAL_EPSILON: float = 1e-6

# Minimum expected baseline reading under active white LED illumination in optical chamber
MIN_OPERATIONAL_REFERENCE_COUNT: float = 100.0


# ============================================================================
# Custom Domain Exceptions
# ============================================================================

class ValidationError(Exception):
    """Base exception for all schema and data validation errors."""
    pass


class MalformedMessageError(ValidationError):
    """Raised when an incoming or outgoing message structure is invalid or corrupt."""
    pass


class InvalidNumericValueError(ValidationError):
    """Raised when numeric data is NaN, infinite, out of bounds, or non-numeric."""
    pass


class OpticalChamberError(ValidationError):
    """Raised when optical sensor baseline is unusable (e.g. LED failure or saturated background)."""
    pass


class DecisionExpiryError(ValidationError):
    """Raised when a decision response is stale or received after deadline."""
    pass


class MismatchedRequestIdError(ValidationError):
    """Raised when a decision response request_id does not match active request."""
    pass


class DuplicateResponseError(ValidationError):
    """Raised when a decision response request_id has already been processed (replay protection)."""
    pass


class FutureTimestampError(ValidationError):
    """Raised when a timestamp claims to be from the future beyond acceptable clock drift."""
    pass


class ActuatorLimitError(ValidationError):
    """Raised when an actuator movement exceeds configured safety limits."""
    pass


# ============================================================================
# Permitted Decision Outcomes
# ============================================================================

class SortingDecision(str, Enum):
    """
    Permitted sorting decisions for ReflectSort.
    Enforced by the DecisionValidator before any actuator movement.
    """
    BIN_A = "BIN_A"                     # Destination Bin A (e.g., Light Shade)
    BIN_B = "BIN_B"                     # Destination Bin B (e.g., Medium Shade)
    BIN_C = "BIN_C"                     # Destination Bin C (e.g., Dark Shade)
    REJECT_UNKNOWN = "REJECT_UNKNOWN"   # Reject chute for unclassifiable or foreign items
    HOLD = "HOLD"                       # Safe hold position / do not actuate / error fallback

    @classmethod
    def is_valid_decision(cls, value: str) -> bool:
        """Check if a string represents a valid SortingDecision enum value."""
        return isinstance(value, str) and value in cls._value2member_map_


# ============================================================================
# Sensor Record Schema
# ============================================================================

@dataclass
class SensorRecord:
    """
    Structured record representing optical and electrical sensor readings
    obtained during a single measurement cycle.

    All simulated records MUST have `data_source="simulated"`.
    """
    specimen_id: str
    run_id: str
    sample_LDR: float
    ambient_LDR: float
    reference_value: float
    sample_position: str
    angle: float
    LED_setting: str
    timestamp: str
    data_source: str = "simulated"
    derived_features: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Automatically validate fields upon instantiation."""
        self.validate()

    @staticmethod
    def _validate_numeric(
        name: str,
        val: Any,
        min_val: float = DEFAULT_MIN_ADC_COUNT,
        max_val: float = DEFAULT_MAX_ADC_COUNT,
    ) -> float:
        """Verify numeric values are real, finite numbers within valid ADC range."""
        if val is None or not isinstance(val, (int, float)) or isinstance(val, bool):
            raise InvalidNumericValueError(
                f"Field '{name}' must be a numeric float or int, got {type(val).__name__} ({val})"
            )
        float_val = float(val)
        if math.isnan(float_val):
            raise InvalidNumericValueError(f"Field '{name}' cannot be NaN")
        if math.isinf(float_val):
            raise InvalidNumericValueError(f"Field '{name}' cannot be infinite (+inf/-inf)")
        if not (min_val <= float_val <= max_val):
            raise InvalidNumericValueError(
                f"Field '{name}' value {float_val} is out of permitted range [{min_val}, {max_val}]"
            )
        return float_val

    def validate(self) -> None:
        """
        Strict validation of the sensor record fields.
        Raises ValidationError or subclasses if invalid.
        """
        # 1. String identifiers validation
        if not isinstance(self.specimen_id, str) or not self.specimen_id.strip():
            raise MalformedMessageError(f"specimen_id must be a non-empty string, got: {self.specimen_id!r}")
        if not isinstance(self.run_id, str) or not self.run_id.strip():
            raise MalformedMessageError(f"run_id must be a non-empty string, got: {self.run_id!r}")
        if not isinstance(self.sample_position, str) or not self.sample_position.strip():
            raise MalformedMessageError(f"sample_position must be a non-empty string, got: {self.sample_position!r}")
        if not isinstance(self.LED_setting, str) or not self.LED_setting.strip():
            raise MalformedMessageError(f"LED_setting must be a non-empty string, got: {self.LED_setting!r}")

        # 2. Numeric ADC counts validation (12-bit ADC range 0.0 to 4095.0)
        self.sample_LDR = self._validate_numeric("sample_LDR", self.sample_LDR, DEFAULT_MIN_ADC_COUNT, DEFAULT_MAX_ADC_COUNT)
        self.ambient_LDR = self._validate_numeric("ambient_LDR", self.ambient_LDR, DEFAULT_MIN_ADC_COUNT, DEFAULT_MAX_ADC_COUNT)
        self.reference_value = self._validate_numeric("reference_value", self.reference_value, DEFAULT_MIN_ADC_COUNT, DEFAULT_MAX_ADC_COUNT)

        # 3. Angle validation (-180.0 to +180.0 degrees)
        self.angle = self._validate_numeric("angle", self.angle, -180.0, 180.0)

        # 4. Data source tag check
        if self.data_source != "simulated":
            raise ValidationError(
                f"Invalid data_source '{self.data_source}'. Software simulation must explicitly label 'simulated'."
            )

        # 5. Timestamp validation
        if not isinstance(self.timestamp, str) or not self.timestamp.strip():
            raise MalformedMessageError("timestamp must be a non-empty ISO 8601 string")
        try:
            ts_str = self.timestamp.replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception as e:
            raise MalformedMessageError(f"timestamp '{self.timestamp}' is not valid ISO 8601: {e}") from e

        # 6. Derived features validation if present
        if not isinstance(self.derived_features, dict):
            raise MalformedMessageError("derived_features must be a dictionary")
        for k, v in self.derived_features.items():
            if not isinstance(k, str):
                raise MalformedMessageError(f"derived_features key must be string, got {type(k)}")
            self._validate_numeric(f"derived_features.{k}", v, -1e6, 1e6)

    def is_optical_baseline_usable(self, min_reference: float = MIN_OPERATIONAL_REFERENCE_COUNT) -> bool:
        """
        Check if the reference sensor baseline reading indicates functional optical illumination.
        If reference_value < min_reference, illumination is inadequate or sensor is obstructed.
        """
        return self.reference_value >= min_reference

    def compute_standard_derived_features(self) -> Dict[str, float]:
        """
        Compute standard derived optical contrast and differential metrics.
        Guarantees zero-division safety and finite results for all valid ADC inputs.

        - differential_LDR: sample_LDR - ambient_LDR
        - contrast_ratio: (sample_LDR - ambient_LDR) / reference_value (safe if ref ~ 0)
        - ambient_ratio: sample_LDR / max(ambient_LDR, EPSILON)
        """
        diff = self.sample_LDR - self.ambient_LDR

        # Safe contrast calculation (guarding against zero or near-zero reference)
        if self.reference_value > NUMERICAL_EPSILON:
            contrast = diff / self.reference_value
        else:
            contrast = 0.0

        # Safe ambient ratio (guarding against zero or near-zero ambient)
        safe_denom = max(self.ambient_LDR, NUMERICAL_EPSILON)
        amb_ratio = self.sample_LDR / safe_denom

        # Ensure all numbers are finite
        if not math.isfinite(diff) or not math.isfinite(contrast) or not math.isfinite(amb_ratio):
            raise InvalidNumericValueError("Non-finite derived feature encountered during calculation")

        self.derived_features = {
            "differential_LDR": round(diff, 3),
            "contrast_ratio": round(contrast, 5),
            "ambient_ratio": round(amb_ratio, 5),
        }
        return self.derived_features

    def to_voltages(self, vref: float = DEFAULT_ADC_VREF_VOLTS) -> Dict[str, float]:
        """
        Convert raw 12-bit ADC counts to estimated physical analog voltages (0.0V - 3.3V).
        Clearly distinguishes raw ADC digital counts from physical analog volts.
        """
        if vref <= 0:
            raise ValidationError(f"vref must be positive, got {vref}")
        return {
            "sample_voltage_V": round((self.sample_LDR / DEFAULT_MAX_ADC_COUNT) * vref, 4),
            "ambient_voltage_V": round((self.ambient_LDR / DEFAULT_MAX_ADC_COUNT) * vref, 4),
            "reference_voltage_V": round((self.reference_value / DEFAULT_MAX_ADC_COUNT) * vref, 4),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert the record to a standard dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SensorRecord:
        """Construct and validate a SensorRecord from dictionary data."""
        if not isinstance(data, dict):
            raise MalformedMessageError(f"Expected dictionary for SensorRecord, got {type(data).__name__}")
        required_fields = [
            "specimen_id", "run_id", "sample_LDR", "ambient_LDR",
            "reference_value", "sample_position", "angle", "LED_setting", "timestamp"
        ]
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise MalformedMessageError(f"Missing required fields in SensorRecord: {missing}")

        return cls(
            specimen_id=data["specimen_id"],
            run_id=data["run_id"],
            sample_LDR=data["sample_LDR"],
            ambient_LDR=data["ambient_LDR"],
            reference_value=data["reference_value"],
            sample_position=data["sample_position"],
            angle=data["angle"],
            LED_setting=data["LED_setting"],
            timestamp=data["timestamp"],
            data_source=data.get("data_source", "simulated"),
            derived_features=data.get("derived_features", {}),
        )

    def to_model_features(self) -> Dict[str, float]:
        """
        Extract numerical features formatted for Kuldeep's ML classification pipeline.
        Note: Exact feature set and ordering are subject to agreement with ML member (Kuldeep).
        """
        features: Dict[str, float] = {
            "sample_LDR": self.sample_LDR,
            "ambient_LDR": self.ambient_LDR,
            "reference_value": self.reference_value,
        }
        if self.derived_features:
            features.update(self.derived_features)
        return features


# ============================================================================
# Decision Request & Response Schemas (Host <-> Firmware / App Protocol)
# ============================================================================

@dataclass
class DecisionRequest:
    """
    Message sent from MCU/Firmware simulator to Python host application
    requesting a shade classification for a measured specimen.
    """
    request_id: str
    features: Dict[str, float]
    timestamp: str
    type: str = "measurement"
    data_source: str = "simulated"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not isinstance(self.request_id, str) or not self.request_id.strip():
            raise MalformedMessageError(f"request_id must be non-empty string, got: {self.request_id!r}")
        if self.type != "measurement":
            raise MalformedMessageError(f"DecisionRequest type must be 'measurement', got: {self.type!r}")
        if self.data_source != "simulated":
            raise ValidationError(f"data_source must be 'simulated', got: {self.data_source!r}")
        if not isinstance(self.features, dict) or len(self.features) == 0:
            raise MalformedMessageError("DecisionRequest must contain a non-empty 'features' dictionary")
        for k, v in self.features.items():
            if not isinstance(k, str):
                raise MalformedMessageError(f"feature key must be string, got: {type(k)}")
            if v is None or not isinstance(v, (int, float)) or isinstance(v, bool) or math.isnan(float(v)) or math.isinf(float(v)):
                raise InvalidNumericValueError(f"feature '{k}' must be finite numeric, got: {v}")
        if not isinstance(self.timestamp, str) or not self.timestamp.strip():
            raise MalformedMessageError("timestamp must be non-empty string")
        try:
            ts_str = self.timestamp.replace("Z", "+00:00")
            datetime.fromisoformat(ts_str)
        except Exception as e:
            raise MalformedMessageError(f"timestamp '{self.timestamp}' is invalid ISO 8601: {e}") from e

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json_line(self) -> str:
        """Serialize to a single newline-delimited JSON line for serial communication."""
        return json.dumps(self.to_dict()) + "\n"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DecisionRequest:
        if not isinstance(data, dict):
            raise MalformedMessageError(f"Expected dict, got {type(data).__name__}")
        required = ["request_id", "features", "timestamp"]
        missing = [f for f in required if f not in data]
        if missing:
            raise MalformedMessageError(f"Missing required fields in DecisionRequest: {missing}")
        return cls(
            request_id=data["request_id"],
            features=data["features"],
            timestamp=data["timestamp"],
            type=data.get("type", "measurement"),
            data_source=data.get("data_source", "simulated"),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_json_line(cls, line: str) -> DecisionRequest:
        """Parse from a raw string or JSON line."""
        if not isinstance(line, str) or not line.strip():
            raise MalformedMessageError("Empty or non-string input line")
        try:
            data = json.loads(line.strip())
        except Exception as e:
            raise MalformedMessageError(f"Invalid JSON line formatting: {e}") from e
        return cls.from_dict(data)


@dataclass
class DecisionResponse:
    """
    Message returned by Python host ML application back to MCU/Firmware simulator
    containing the classification label and confidence.
    """
    request_id: str
    label: str
    timestamp: str
    type: str = "decision"
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not isinstance(self.request_id, str) or not self.request_id.strip():
            raise MalformedMessageError(f"request_id must be non-empty string, got: {self.request_id!r}")
        if self.type != "decision":
            raise MalformedMessageError(f"DecisionResponse type must be 'decision', got: {self.type!r}")
        if not isinstance(self.label, str) or not self.label.strip():
            raise MalformedMessageError(f"label must be a non-empty string, got: {self.label!r}")
        if not SortingDecision.is_valid_decision(self.label):
            raise ValidationError(
                f"Unsupported label '{self.label}'. Permitted labels: {[d.value for d in SortingDecision]}"
            )
        if self.confidence is not None:
            if not isinstance(self.confidence, (int, float)) or isinstance(self.confidence, bool):
                raise InvalidNumericValueError(f"confidence must be numeric float, got: {type(self.confidence)}")
            c = float(self.confidence)
            if math.isnan(c) or math.isinf(c) or not (0.0 <= c <= 1.0):
                raise InvalidNumericValueError(f"confidence must be in [0.0, 1.0], got: {c}")
        if not isinstance(self.timestamp, str) or not self.timestamp.strip():
            raise MalformedMessageError("timestamp must be non-empty string")
        try:
            ts_str = self.timestamp.replace("Z", "+00:00")
            datetime.fromisoformat(ts_str)
        except Exception as e:
            raise MalformedMessageError(f"timestamp '{self.timestamp}' is invalid ISO 8601: {e}") from e

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json_line(self) -> str:
        """Serialize to a single newline-delimited JSON line for serial communication."""
        return json.dumps(self.to_dict()) + "\n"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DecisionResponse:
        if not isinstance(data, dict):
            raise MalformedMessageError(f"Expected dict, got {type(data).__name__}")
        required = ["request_id", "label", "timestamp"]
        missing = [f for f in required if f not in data]
        if missing:
            raise MalformedMessageError(f"Missing required fields in DecisionResponse: {missing}")
        return cls(
            request_id=data["request_id"],
            label=data["label"],
            timestamp=data["timestamp"],
            type=data.get("type", "decision"),
            confidence=data.get("confidence"),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_json_line(cls, line: str) -> DecisionResponse:
        """Parse from a raw string or JSON line."""
        if not isinstance(line, str) or not line.strip():
            raise MalformedMessageError("Empty or non-string input line")
        try:
            data = json.loads(line.strip())
        except Exception as e:
            raise MalformedMessageError(f"Invalid JSON line formatting: {e}") from e
        return cls.from_dict(data)


# ============================================================================
# Actuator Event Schema
# ============================================================================

@dataclass
class ActuatorEvent:
    """
    Log record of an actuator action attempted or executed by the diverter simulator.
    Tracks previous angle, target angle, resulting angle, status, and reason.
    """
    event_id: str
    timestamp: str
    request_id: str
    decision: str
    previous_angle_deg: float
    target_angle_deg: float
    resulting_angle_deg: float
    status: str                         # "EXECUTED", "HELD", "REJECTED"
    reason: str
    is_simulated: bool = True
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ActuatorEvent:
        if not isinstance(data, dict):
            raise MalformedMessageError("Expected dict for ActuatorEvent")
        prev = float(data.get("previous_angle_deg", data.get("target_angle_deg", 90.0)))
        target = float(data.get("target_angle_deg", 90.0))
        result = float(data.get("resulting_angle_deg", target))
        return cls(
            event_id=data["event_id"],
            timestamp=data["timestamp"],
            request_id=data["request_id"],
            decision=data["decision"],
            previous_angle_deg=prev,
            target_angle_deg=target,
            resulting_angle_deg=result,
            status=data["status"],
            reason=data["reason"],
            is_simulated=data.get("is_simulated", True),
            details=data.get("details", {}),
        )
