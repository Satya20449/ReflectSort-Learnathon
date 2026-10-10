"""Optional NDJSON serial bridge for ReflectSort.

Protocol: one UTF-8 JSON object per line. Measurement messages use:
{"type":"measurement","request_id":"REQ-001","sample_LDR":1200,
 "ambient_LDR":800,"reference_value":900}

`features` may instead contain the sensor values. The reference value is optional.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from typing import Any, Dict, Optional, Tuple

try:  # Support both package imports and direct script execution.
    from .shade_demo import Predictor, log_prediction
except ImportError:  # pragma: no cover - direct script execution
    from shade_demo import Predictor, log_prediction


class SerialMessageError(ValueError):
    """Raised when a serial line is not a valid ReflectSort measurement."""


def parse_measurement_message(line: str) -> Tuple[str, float, float, Optional[float]]:
    """Parse one NDJSON measurement line into (request_id, sample, ambient, reference)."""
    try:
        payload = json.loads(line)
    except (json.JSONDecodeError, TypeError) as exc:
        raise SerialMessageError(f"Malformed JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SerialMessageError("Message must be a JSON object")
    if payload.get("type") != "measurement":
        raise SerialMessageError("Expected message type 'measurement'")
    request_id = payload.get("request_id")
    if not isinstance(request_id, str) or not request_id.strip():
        raise SerialMessageError("request_id must be a non-empty string")
    features = payload.get("features", payload)
    if not isinstance(features, dict):
        raise SerialMessageError("features must be a JSON object")
    if "sample_LDR" not in features or "ambient_LDR" not in features:
        raise SerialMessageError("sample_LDR and ambient_LDR are required")
    try:
        sample = float(features["sample_LDR"])
        ambient = float(features["ambient_LDR"])
        raw_reference = features.get("reference_value")
        reference = None if raw_reference is None else float(raw_reference)
    except (TypeError, ValueError) as exc:
        raise SerialMessageError("Sensor values must be numeric") from exc
    values = [sample, ambient] + ([] if reference is None else [reference])
    if not all(math.isfinite(value) for value in values):
        raise SerialMessageError("Sensor values must be finite")
    return request_id, sample, ambient, reference


def run_serial_bridge(port: str, baudrate: int = 115200, timeout: float = 2.0) -> None:
    try:
        import serial
    except ImportError:
        print("Error: pyserial package is required for hardware serial reading.")
        print("Install via: python3 -m pip install pyserial")
        return

    predictor = Predictor()
    print(f"Opening serial port '{port}' at {baudrate} baud...")
    print(f"Active Model: {predictor.model_path.name}")
    print("Awaiting NDJSON measurement messages (one JSON object per line)...")
    try:
        with serial.Serial(port, baudrate, timeout=timeout) as ser:
            while True:
                raw = ser.readline()
                if not raw:  # Serial timeout: no complete line received.
                    print("Serial read timeout: no complete message received.")
                    continue
                try:
                    line = raw.decode("utf-8").strip()
                    if not line:
                        continue
                    request_id, sample, ambient, reference = parse_measurement_message(line)
                    decision, confidence, note = predictor.predict(sample, ambient, reference)
                    log_prediction(sample, ambient, reference, decision, confidence, note)
                    print(
                        f"ID={request_id} S={sample:g} A={ambient:g} "
                        f"R={reference if reference is not None else '-'} -> "
                        f"{decision} ({confidence:.2%}) | {note}"
                    )
                except (UnicodeDecodeError, SerialMessageError) as exc:
                    print(f"Ignored invalid NDJSON message: {exc}")
    except KeyboardInterrupt:
        print("\nSerial bridge stopped by user.")
    except Exception as exc:
        print(f"Serial communication error on {port}: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="ReflectSort NDJSON Serial Bridge")
    parser.add_argument("port", nargs="?", default="/dev/ttyACM0", help="Serial port identifier")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("--timeout", type=float, default=2.0, help="Read timeout in seconds")
    args = parser.parse_args()
    run_serial_bridge(args.port, args.baud, args.timeout)


if __name__ == "__main__":
    main()
