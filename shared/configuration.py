"""
ReflectSort — Unified System Configuration & Shared Constants
Course: Machine Learning – Embedded Systems Design (ML-ESD)
Team: ML-ESD-TEAM-117 | Project ID: PROJECT-12-VARIANT-06

Authoritative system constants, feature definitions, validation bounds,
and mapping rules shared across ML, Application, and Embedded Simulation layers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Project root resolution helper
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ============================================================================
# 1. Hardware / Sensor Specifications (12-bit ADC on STM32 NUCLEO-F446RE)
# ============================================================================
ADC_MIN_COUNT: int = 0
ADC_MAX_COUNT: int = 4095
ADC_RESOLUTION_BITS: int = 12
ADC_VREF_VOLTS: float = 3.30
MIN_OPERATIONAL_REFERENCE_COUNT: float = 50.0  # Chamber illumination threshold
NUMERICAL_EPSILON: float = 1e-6

# ============================================================================
# 2. Machine Learning Feature Contract (Member 2 - Kuldeep Singh)
# ============================================================================
EXPECTED_FEATURES: List[str] = ["sample_LDR", "ambient_LDR", "reflectance_ratio"]
TARGET_COLUMN: str = "shade_label"
EXPECTED_CLASSES: List[str] = ["Dark", "Light", "Medium"]
DEFAULT_CONFIDENCE_THRESHOLD: float = 0.60
DEFAULT_RANDOM_SEED: int = 117

# Relative paths for ML artifacts
DEFAULT_MODEL_RELATIVE_PATH: Path = Path("ml") / "model" / "shade_model.joblib"
DEFAULT_DATA_RELATIVE_PATH: Path = Path("ml") / "data" / "demo_data_simulated.csv"
DEFAULT_PREDICTION_LOG_RELATIVE_PATH: Path = Path("application") / "prediction_log.csv"

# ============================================================================
# 3. Decision & Physical Sorting Mappings (Member 3 - Satyam Rai / Member 4 - Ajitesh Karan)
# ============================================================================
LABEL_TO_BIN: Dict[str, str] = {
    "Dark": "BIN_A",
    "Medium": "BIN_B",
    "Light": "BIN_C",
}

# Permitted sorting actions in the host application and MCU safety gate
PERMITTED_SORTING_ACTIONS: Tuple[str, ...] = ("BIN_A", "BIN_B", "BIN_C", "HOLD", "REJECT_UNKNOWN")

# 3-Bin Diverter Angular Calibration (Degrees)
ACTUATOR_ANGLE_MAPPING: Dict[str, float] = {
    "BIN_A": 45.0,           # Dark shade divert chute
    "BIN_B": 90.0,           # Medium shade divert chute (neutral center)
    "BIN_C": 135.0,          # Light shade divert chute
    "HOLD": 90.0,            # Safety / neutral hold position
    "REJECT_UNKNOWN": 180.0, # Unclassified / foreign matter divert chute
}

ACTUATOR_HOME_ANGLE_DEG: float = 90.0
ACTUATOR_MIN_TRAVEL_DEG: float = 0.0
ACTUATOR_MAX_TRAVEL_DEG: float = 180.0
ACTUATOR_SETTLING_TIME_MS: float = 150.0

# ============================================================================
# 4. Temporal Safety & Protocol Policies (Member 4 - Ajitesh Karan)
# ============================================================================
DEFAULT_MAX_RESPONSE_LATENCY_SECONDS: float = 2.0   # Standard timeout boundary
DEFAULT_MAX_FUTURE_CLOCK_DRIFT_SECONDS: float = 0.5 # Max clock drift allowance
DEFAULT_REPLAY_HISTORY_SIZE: int = 256              # FIFO replay protection cache size


# ============================================================================
# 5. Shared Helper Functions
# ============================================================================

def validate_raw_sensor_inputs(
    sample_ldr: Any,
    ambient_ldr: Any,
    reference_value: Optional[Any] = None,
) -> Tuple[bool, str]:
    """
    Validate raw optical sensor ADC counts before feature construction or ML inference.

    Rules:
    - Must be non-None and convertible to float/int.
    - Must be finite (no NaN, inf).
    - Must lie within 12-bit ADC range [0, 4095].
    - ambient_ldr must be strictly positive (> 0) to avoid zero-division in reflectance_ratio.
    - If reference_value is provided, it must also be in [0, 4095].
    """
    # 1. Type & Non-empty check
    if sample_ldr is None or ambient_ldr is None:
        return False, "Missing sensor value: sample_ldr and ambient_ldr are required"

    try:
        sample = float(sample_ldr)
        ambient = float(ambient_ldr)
        ref = float(reference_value) if reference_value not in (None, "") else None
    except (TypeError, ValueError):
        return False, "Sensor readings must be numeric numbers"

    # 2. Finite numeric check
    if not math.isfinite(sample) or not math.isfinite(ambient) or (ref is not None and not math.isfinite(ref)):
        return False, "Sensor readings must be finite numbers (no NaN or Infinity)"

    # 3. Hardware ADC Range Check
    if not (ADC_MIN_COUNT <= sample <= ADC_MAX_COUNT):
        return False, f"sample_ldr={sample:.2f} outside ADC range [{ADC_MIN_COUNT}, {ADC_MAX_COUNT}]"

    if not (ADC_MIN_COUNT <= ambient <= ADC_MAX_COUNT):
        return False, f"ambient_ldr={ambient:.2f} outside ADC range [{ADC_MIN_COUNT}, {ADC_MAX_COUNT}]"

    if ambient <= 0:
        return False, f"ambient_ldr must be > 0 for reflectance calculation (got {ambient})"

    if ref is not None and not (ADC_MIN_COUNT <= ref <= ADC_MAX_COUNT):
        return False, f"reference_value={ref:.2f} outside ADC range [{ADC_MIN_COUNT}, {ADC_MAX_COUNT}]"

    return True, "Valid sensor inputs"


def compute_ml_features(sample_ldr: float, ambient_ldr: float) -> Dict[str, float]:
    """
    Construct the approved 3-feature dictionary for Member 2's model:
    - sample_LDR
    - ambient_LDR
    - reflectance_ratio (= sample_LDR / ambient_LDR)
    """
    safe_ambient = max(ambient_ldr, NUMERICAL_EPSILON)
    ratio = sample_ldr / safe_ambient
    return {
        "sample_LDR": float(sample_ldr),
        "ambient_LDR": float(ambient_ldr),
        "reflectance_ratio": float(ratio),
    }


def map_shade_to_bin(shade_label: str) -> str:
    """
    Map ML shade classification ('Dark', 'Medium', 'Light') to physical sorting bin action.
    Returns 'HOLD' for unrecognized or unmapped labels.
    """
    return LABEL_TO_BIN.get(shade_label, "HOLD")
