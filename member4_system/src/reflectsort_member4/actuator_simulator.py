"""
ReflectSort — Actuator and Sorting Simulator Module
Module: reflectsort_member4.actuator_simulator

Simulates the mechanical diverter response (e.g., servo motor deflector)
to validated sorting commands.

Safety Invariants Enforced:
1. Gated Execution: Only ValidationResult with `is_valid == True` may actuate sorting movements.
2. Failsafe State Updates: On rejection/timeout, actuator enters safe neutral state and state string updates.
3. Accurate Audit Logging: Tracks previous_angle_deg, target_angle_deg, resulting_angle_deg without cross-contamination.
4. Mechanical Limit Guarding: Enforces travel envelope [min_travel_angle, max_travel_angle].
5. Distinct Safety Outcomes: Clearly distinguishes commanded HOLD from safety-blocked rejections in audit logs.
6. Simulation Tagging: All simulated actions and events are marked with `is_simulated=True`.

Author: Ajitesh Karan (2500032236)
Course: Machine Learning – Embedded Systems Design (ML–ESD)
Team: ML-ESD-TEAM-117 (Project 12, Variant 06)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from reflectsort_member4.decision_validator import ValidationResult
from reflectsort_member4.schemas import (
    ActuatorEvent,
    ActuatorLimitError,
    SortingDecision,
    ValidationError,
)

# Standard hobby servo PWM defaults (50Hz / 20ms period)
DEFAULT_PWM_PERIOD_MS: float = 20.0
DEFAULT_MIN_PULSE_WIDTH_MS: float = 1.00   # Corresponding to 0 degrees
DEFAULT_MAX_PULSE_WIDTH_MS: float = 2.00   # Corresponding to 180 degrees


@dataclass
class ActuatorConfig:
    """
    Configuration for the simulated sorting diverter mechanism.

    DISCLAIMER: Angular positions and pulse widths are simulation defaults.
    Physical servo angles must be calibrated on the physical test rig.
    """
    diverter_mode: str = "THREE_BIN"          # "TWO_BIN" or "THREE_BIN"
    min_travel_angle_deg: float = 0.0          # Minimum travel limit
    max_travel_angle_deg: float = 180.0        # Maximum travel limit
    home_angle_deg: float = 90.0               # Neutral / Hold position
    settling_time_ms: float = 120.0            # Simulated actuation settling time
    reject_action_behavior: str = "RETURN_TO_HOME"  # "RETURN_TO_HOME" (safe default) or "FREEZE_CURRENT"

    # Default preliminary angular mapping (subject to physical calibration)
    angle_mapping: Dict[str, float] = field(
        default_factory=lambda: {
            SortingDecision.BIN_A.value: 45.0,           # Chute A (e.g. Light shade)
            SortingDecision.BIN_B.value: 90.0,           # Chute B (e.g. Medium shade)
            SortingDecision.BIN_C.value: 135.0,          # Chute C (e.g. Dark shade)
            SortingDecision.REJECT_UNKNOWN.value: 165.0, # Reject chute
            SortingDecision.HOLD.value: 90.0,            # Neutral hold
        }
    )

    def validate(self) -> None:
        if self.min_travel_angle_deg < 0:
            raise ValidationError("min_travel_angle_deg cannot be negative")
        if self.max_travel_angle_deg <= self.min_travel_angle_deg:
            raise ValidationError("max_travel_angle_deg must be greater than min_travel_angle_deg")
        if not (self.min_travel_angle_deg <= self.home_angle_deg <= self.max_travel_angle_deg):
            raise ValidationError("home_angle_deg must be within [min_travel_angle_deg, max_travel_angle_deg]")
        if self.reject_action_behavior not in ("RETURN_TO_HOME", "FREEZE_CURRENT"):
            raise ValidationError(
                f"Invalid reject_action_behavior '{self.reject_action_behavior}'. Allowed: 'RETURN_TO_HOME', 'FREEZE_CURRENT'"
            )
        for label, angle in self.angle_mapping.items():
            if not (self.min_travel_angle_deg <= angle <= self.max_travel_angle_deg):
                raise ValidationError(
                    f"Configured angle {angle}° for '{label}' exceeds travel limits [{self.min_travel_angle_deg}°, {self.max_travel_angle_deg}°]"
                )


class ActuatorSimulator:
    """
    Software simulator for the ReflectSort servo-driven diverter.
    Tracks state, executes gated decisions, enforces travel limits, and logs actions.
    """

    def __init__(self, config: Optional[ActuatorConfig] = None) -> None:
        self.config = config or ActuatorConfig()
        self.config.validate()

        self.current_angle_deg: float = self.config.home_angle_deg
        self.current_state: str = "HOME_HOLD"
        self.last_decision: Optional[str] = SortingDecision.HOLD.value
        self.action_history: List[ActuatorEvent] = []
        self._action_counter: int = 0

    def angle_to_pulse_width_ms(self, angle_deg: float) -> float:
        """
        Convert angular position (0-180 deg) to estimated 50Hz PWM pulse width (1.0ms - 2.0ms).
        Formula: pulse_ms = 1.0ms + (angle_deg / 180.0) * (2.0ms - 1.0ms)
        """
        clamped_angle = max(self.config.min_travel_angle_deg, min(self.config.max_travel_angle_deg, angle_deg))
        travel_span = self.config.max_travel_angle_deg - self.config.min_travel_angle_deg
        fraction = (clamped_angle - self.config.min_travel_angle_deg) / travel_span if travel_span > 0 else 0.5
        pulse_width = DEFAULT_MIN_PULSE_WIDTH_MS + fraction * (DEFAULT_MAX_PULSE_WIDTH_MS - DEFAULT_MIN_PULSE_WIDTH_MS)
        return round(pulse_width, 4)

    def get_current_position(self) -> Dict[str, Any]:
        """Return the current simulated actuator state, position, and pulse width."""
        return {
            "current_angle_deg": self.current_angle_deg,
            "estimated_pulse_width_ms": self.angle_to_pulse_width_ms(self.current_angle_deg),
            "current_state": self.current_state,
            "last_decision": self.last_decision,
            "is_simulated": True,
        }

    def home(self) -> ActuatorEvent:
        """Move the actuator back to the neutral/home hold position."""
        self._action_counter += 1
        now_ts = datetime.now(timezone.utc).isoformat()
        prev_angle = self.current_angle_deg
        self.current_angle_deg = self.config.home_angle_deg
        self.current_state = "HOME_HOLD"
        self.last_decision = SortingDecision.HOLD.value

        event = ActuatorEvent(
            event_id=f"ACT-EVT-{self._action_counter:05d}",
            timestamp=now_ts,
            request_id="SYS_HOME",
            decision=SortingDecision.HOLD.value,
            previous_angle_deg=prev_angle,
            target_angle_deg=self.config.home_angle_deg,
            resulting_angle_deg=self.config.home_angle_deg,
            status="HELD",
            reason="Actuator reset to neutral home position",
            is_simulated=True,
            details={
                "angle_deg": self.current_angle_deg,
                "pulse_width_ms": self.angle_to_pulse_width_ms(self.current_angle_deg),
            },
        )
        self.action_history.append(event)
        return event

    def execute_decision(self, validation: ValidationResult) -> ActuatorEvent:
        """
        Execute an actuation command based on the output of DecisionValidator.

        Safety Policies:
        - If validation.is_valid is False:
            - Under RETURN_TO_HOME: returns to neutral home (90°), sets state to SAFETY_BLOCKED_HOME.
            - Under FREEZE_CURRENT: holds position, sets state to SAFETY_BLOCKED_FROZEN.
            - Records status="REJECTED", tracks previous angle and target angle.
        - If action is HOLD: transitions to neutral home position (90°), sets state to HOLD_NEUTRAL, records status="HELD".
        - If action is a valid sorting label: moves to mapped angle, sets state to DIVERT_<LABEL>, records status="EXECUTED".
        """
        self._action_counter += 1
        now_ts = datetime.now(timezone.utc).isoformat()
        evt_id = f"ACT-EVT-{self._action_counter:05d}"
        prev_angle = self.current_angle_deg

        # Safety Gate 1: Check validation status
        if not validation.is_valid:
            if self.config.reject_action_behavior == "RETURN_TO_HOME":
                self.current_angle_deg = self.config.home_angle_deg
                self.current_state = "SAFETY_BLOCKED_HOME"
                resulting_angle = self.config.home_angle_deg
            else:
                self.current_state = "SAFETY_BLOCKED_FROZEN"
                resulting_angle = prev_angle

            self.last_decision = f"BLOCKED_{validation.original_label or 'INVALID'}"

            event = ActuatorEvent(
                event_id=evt_id,
                timestamp=now_ts,
                request_id=validation.request_id,
                decision=validation.validated_action.value,
                previous_angle_deg=prev_angle,
                target_angle_deg=resulting_angle,
                resulting_angle_deg=resulting_angle,
                status="REJECTED",
                reason=f"Movement blocked by safety validator: {validation.reason}",
                is_simulated=True,
                details={
                    "error_code": validation.error_code,
                    "attempted_label": validation.original_label,
                    "held_angle_deg": self.current_angle_deg,
                    "pulse_width_ms": self.angle_to_pulse_width_ms(self.current_angle_deg),
                },
            )
            self.action_history.append(event)
            return event

        action = validation.validated_action

        # Safety Gate 2: Handle explicit or validated HOLD
        if action == SortingDecision.HOLD:
            self.current_angle_deg = self.config.home_angle_deg
            self.current_state = "HOLD_NEUTRAL"
            self.last_decision = action.value
            event = ActuatorEvent(
                event_id=evt_id,
                timestamp=now_ts,
                request_id=validation.request_id,
                decision=action.value,
                previous_angle_deg=prev_angle,
                target_angle_deg=self.config.home_angle_deg,
                resulting_angle_deg=self.config.home_angle_deg,
                status="HELD",
                reason=f"Hold action confirmed ({validation.reason})",
                is_simulated=True,
                details={
                    "angle_deg": self.current_angle_deg,
                    "pulse_width_ms": self.angle_to_pulse_width_ms(self.current_angle_deg),
                },
            )
            self.action_history.append(event)
            return event

        # Safety Gate 3: Resolve target angle from mapping
        target_angle = self.config.angle_mapping.get(action.value)
        if target_angle is None:
            self.current_angle_deg = self.config.home_angle_deg
            self.current_state = "SAFETY_BLOCKED_UNMAPPED"
            self.last_decision = f"UNMAPPED_{action.value}"
            event = ActuatorEvent(
                event_id=evt_id,
                timestamp=now_ts,
                request_id=validation.request_id,
                decision=action.value,
                previous_angle_deg=prev_angle,
                target_angle_deg=self.config.home_angle_deg,
                resulting_angle_deg=self.config.home_angle_deg,
                status="REJECTED",
                reason=f"No angle mapping configured for action '{action.value}'",
                is_simulated=True,
                details={"held_angle_deg": self.current_angle_deg},
            )
            self.action_history.append(event)
            return event

        # Safety Gate 4: Enforce travel limits
        if not (self.config.min_travel_angle_deg <= target_angle <= self.config.max_travel_angle_deg):
            self.current_angle_deg = self.config.home_angle_deg
            self.current_state = "SAFETY_BLOCKED_LIMIT"
            self.last_decision = f"LIMIT_EXCEEDED_{action.value}"
            event = ActuatorEvent(
                event_id=evt_id,
                timestamp=now_ts,
                request_id=validation.request_id,
                decision=action.value,
                previous_angle_deg=prev_angle,
                target_angle_deg=self.config.home_angle_deg,
                resulting_angle_deg=self.config.home_angle_deg,
                status="REJECTED",
                reason=(
                    f"Target angle {target_angle}° exceeds safety limits "
                    f"[{self.config.min_travel_angle_deg}°, {self.config.max_travel_angle_deg}°]"
                ),
                is_simulated=True,
                details={"held_angle_deg": self.current_angle_deg},
            )
            self.action_history.append(event)
            return event

        # Execution of validated movement
        self.current_angle_deg = target_angle
        self.current_state = f"DIVERT_{action.value}"
        self.last_decision = action.value

        event = ActuatorEvent(
            event_id=evt_id,
            timestamp=now_ts,
            request_id=validation.request_id,
            decision=action.value,
            previous_angle_deg=prev_angle,
            target_angle_deg=target_angle,
            resulting_angle_deg=target_angle,
            status="EXECUTED",
            reason=f"Diverter successfully actuated to {target_angle}° for {action.value}",
            is_simulated=True,
            details={
                "settling_time_ms": self.config.settling_time_ms,
                "pulse_width_ms": self.angle_to_pulse_width_ms(target_angle),
                "confidence": validation.confidence,
                "latency_seconds": validation.latency_seconds,
            },
        )
        self.action_history.append(event)
        return event

    def get_history(self) -> List[ActuatorEvent]:
        """Return the complete chronological action log."""
        return list(self.action_history)

    def clear_history(self) -> None:
        """Clear the action log history."""
        self.action_history.clear()
