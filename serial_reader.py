"""Optional serial bridge. Expected CSV line: sample_ldr,ambient_ldr[,reference_value].
Confirm port, baud rate and message format with the firmware member before use.
"""
import sys
import serial
from shade_demo import Predictor, log_row

port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
pred = Predictor()
print(f"Listening on {port} at 115200 baud | {pred.source}")
with serial.Serial(port, 115200, timeout=2) as ser:
    while True:
        line = ser.readline().decode(errors="ignore").strip()
        if not line:
            continue
        try:
            vals = [float(v.strip()) for v in line.split(",")]
            if len(vals) not in (2, 3):
                raise ValueError
            sample, ambient = vals[:2]
            reference = vals[2] if len(vals) == 3 else None
        except ValueError:
            print("Ignored malformed serial line:", line)
            continue
        label, conf, note = pred.predict(sample, ambient, reference)
        log_row(sample, ambient, reference, label, conf, note)
        print(f"S={sample} A={ambient} R={reference or '-'} -> {label} ({conf:.2f}) | {note}")
