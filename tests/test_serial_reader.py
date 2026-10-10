"""Mock-only tests for the NDJSON serial bridge; no hardware is required."""
import json
import sys
import types

import pytest

from application.serial_reader import SerialMessageError, parse_measurement_message, run_serial_bridge


def test_parse_valid_ndjson_measurement():
    msg = json.dumps({"type": "measurement", "request_id": "REQ-1", "features": {
        "sample_LDR": 1200, "ambient_LDR": 800, "reference_value": 900
    }})
    assert parse_measurement_message(msg) == ("REQ-1", 1200.0, 800.0, 900.0)


def test_parse_valid_message_without_optional_reference():
    msg = json.dumps({"type": "measurement", "request_id": "REQ-2", "sample_LDR": 1200, "ambient_LDR": 800})
    assert parse_measurement_message(msg) == ("REQ-2", 1200.0, 800.0, None)


@pytest.mark.parametrize("line", ["not json", "[]", "{}", '{"type":"decision"}',
                                    '{"type":"measurement","request_id":"R","sample_LDR":"bad","ambient_LDR":1}',
                                    '{"type":"measurement","request_id":"R","sample_LDR":NaN,"ambient_LDR":1}'])
def test_malformed_messages_rejected(line):
    with pytest.raises(SerialMessageError):
        parse_measurement_message(line)


def test_serial_timeout_and_communication_failure_are_reported(monkeypatch, capsys):
    class FakePredictor:
        model_path = type("P", (), {"name": "fake.joblib"})()
        def predict(self, *args):
            return "BIN_A", 0.9, "mock"

    class FakeSerial:
        def __init__(self, *args, **kwargs):
            self.reads = iter([b"", OSError("device disconnected")])
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def readline(self):
            value = next(self.reads)
            if isinstance(value, Exception): raise value
            return value

    fake_serial_module = types.SimpleNamespace(Serial=FakeSerial)
    monkeypatch.setitem(sys.modules, "serial", fake_serial_module)
    import application.serial_reader as reader
    monkeypatch.setattr(reader, "Predictor", FakePredictor)
    run_serial_bridge("MOCK", timeout=0.01)
    output = capsys.readouterr().out
    assert "Serial read timeout" in output
    assert "Serial communication error" in output


def test_serial_bridge_processes_valid_message_and_ignores_malformed(monkeypatch, capsys):
    valid = json.dumps({"type":"measurement", "request_id":"REQ-3", "sample_LDR":1200, "ambient_LDR":800}) + "\n"
    class FakePredictor:
        model_path = type("P", (), {"name": "fake.joblib"})()
        def predict(self, *args): return "BIN_A", 0.9, "mock prediction"
    class FakeSerial:
        def __init__(self, *args, **kwargs): self.reads = iter([b"oops\n", valid.encode(), KeyboardInterrupt()])
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def readline(self):
            value = next(self.reads)
            if isinstance(value, BaseException): raise value
            return value
    monkeypatch.setitem(sys.modules, "serial", types.SimpleNamespace(Serial=FakeSerial))
    import application.serial_reader as reader
    monkeypatch.setattr(reader, "Predictor", FakePredictor)
    monkeypatch.setattr(reader, "log_prediction", lambda *args: None)
    run_serial_bridge("MOCK")
    output = capsys.readouterr().out
    assert "Ignored invalid NDJSON message" in output
    assert "ID=REQ-3" in output
    assert "stopped by user" in output
