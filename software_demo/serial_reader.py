"""
OPTIONAL - use when Member 4's board is ready.
Expected line from the board over USB serial, e.g.:   1234,500,1800
(sample_ldr, ambient_ldr, reference_value). Agree the exact format with Member 4.
Usage:  python serial_reader.py COM3        (Linux/Mac: /dev/ttyACM0)
"""
import sys
import serial                      # pip install pyserial
from shade_demo import Predictor, log_row

port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
pred = Predictor()
print("Listening on", port, "|", pred.source)
with serial.Serial(port, 115200, timeout=2) as ser:
    while True:
        line = ser.readline().decode(errors="ignore").strip()
        if not line:
            continue
        try:
            s, a, r = (int(v) for v in line.split(","))
        except ValueError:
            print("Ignored malformed line:", line)
            continue
        label, conf, note = pred.predict(s, a, r)
        log_row(s, a, r, label, conf, note)
        print(f"S={s} A={a} R={r} -> {label} ({conf:.2f}) {note}")
