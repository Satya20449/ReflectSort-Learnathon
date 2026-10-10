# ReflectSort — Authoritative Interface Contract

**Project ID:** PROJECT-12-VARIANT-06  
**Team:** ML-ESD-TEAM-117  
**Status:** Unified Authoritative Interface Specification  
**Members:**
- **Kuldeep Singh** (Member 2 — Machine Learning & Dataset)
- **Satyam Rai** (Member 3 — Python Software Application)
- **Ajitesh Karan** (Member 4 — System Architecture, Simulation & Validation)
- **Satya Nayak** (Team Lead — Integration & Delivery)

---

## 1. System Overview & Architecture

ReflectSort is an optical mini-sorting cell prototype that evaluates grain/seed shade using photodiode/LDR reflectance measurements. The software pipeline is structured into three cooperating domains:

```
+-----------------------------+       NDJSON Request       +------------------------------------+
| Member 4: Embedded Sensing  | -------------------------> | Member 3: Python Application Layer |
| - Optical Chamber LDR / LED |                            | - GUI / CLI Interface              |
| - 12-bit ADC (0 - 4095)     | <------------------------- | - Feature Extraction & Preprocess  |
| - Decision Safety Gate      |       NDJSON Response      | - Prediction Logging               |
| - Diverter Actuator Model   |                            +------------------------------------+
+-----------------------------+                                               |
                                                                              v
                                                           +------------------------------------+
                                                           | Member 2: ML Model Pipeline        |
                                                           | - StandardScaler Preprocessing     |
                                                           | - RandomForestClassifier (seed=117)|
                                                           | - 3-Feature Contract               |
                                                           +------------------------------------+
```

---

## 2. Authoritative ML Feature Contract

The machine-learning pipeline expects exactly **three ordered numerical features**:

| Index | Feature Name | Description | Calculation | Unit / Range |
|---|---|---|---|---|
| 0 | `sample_LDR` | Reflected light from grain sample | Direct 12-bit ADC | $[0, 4095]$ integer counts |
| 1 | `ambient_LDR` | Ambient optical background reading | Direct 12-bit ADC | $[1, 4095]$ integer counts ($>0$) |
| 2 | `reflectance_ratio` | Normalised reflectance index | $\text{sample\_LDR} / \text{ambient\_LDR}$ | $[0.0, \infty)$ dimensionless float |

### Rules & Preprocessing Guards:
1. **Feature Ordering:** Features passed to the scikit-learn pipeline must strictly follow `['sample_LDR', 'ambient_LDR', 'reflectance_ratio']`.
2. **Scaler Inclusion:** The model artifact `shade_model.joblib` embeds a `StandardScaler` inside the pipeline. Host code must **not** manually scale inputs before passing them to the pipeline.
3. **Training Range Validation:** The model artifact specifies training range bounds (`training_min` and `training_max`). Inputs outside these bounds are rejected and routed to `HOLD` to prevent uncontrolled extrapolation.
4. **Reference Value Usage:** The optional `reference_value` (e.g. optical calibration baseline) is recorded for audit logging and firmware diagnostic validation, but is **not** fed into the 3-feature model.

---

## 3. Classification Labels & Physical Sorting Mapping

### Classification Output:
The ML model outputs one of three nominal shade classes:
- `"Dark"` (Low reflectance band)
- `"Medium"` (Moderate reflectance band)
- `"Light"` (High reflectance band)

### Actuator Bin Mapping:
| ML Model Shade Label | Proposed Sorting Action | Diverter Servo Angle | Physical Chute Function |
|---|---|---|---|
| `"Dark"` | `BIN_A` | $45.0^\circ$ | Dark shade collection bin |
| `"Medium"` | `BIN_B` | $90.0^\circ$ | Medium shade collection bin (Neutral center) |
| `"Light"` | `BIN_C` | $135.0^\circ$ | Light shade collection bin |
| *Validation Failure / Low Conf* | `HOLD` | $90.0^\circ$ | Safe neutral holding chute |
| *Unrecognized / Foreign Object* | `REJECT_UNKNOWN` | $180.0^\circ$ | Divert to reject collection |

### Confidence Threshold:
- **Default Minimum Confidence:** $\ge 0.60$ ($60\%$).
- Predictions with probability $< 0.60$ must return `HOLD` with a documented reason.

---

## 4. Communication Protocol (NDJSON Framing)

When operating over UART serial or software IPC, messages are framed as **Newline-Delimited JSON (NDJSON)**.

### A. Measurement Request (MCU / Simulator $\rightarrow$ Host Application)
Sent when a grain specimen is illuminated in the optical chamber.

```json
{
  "type": "measurement",
  "request_id": "REQ-SEED-0042",
  "data_source": "simulated",
  "timestamp": "2026-10-10T12:00:00.000000+00:00",
  "features": {
    "sample_LDR": 510.0,
    "ambient_LDR": 150.0,
    "reflectance_ratio": 3.40,
    "reference_value": 900.0
  },
  "metadata": {
    "specimen_id": "SEED-0042",
    "run_id": "RUN-01"
  }
}
```

### B. Decision Response (Host Application $\rightarrow$ MCU / Validator Gate)
Returned by the Python application back to the controller.

```json
{
  "type": "decision",
  "request_id": "REQ-SEED-0042",
  "label": "BIN_B",
  "confidence": 0.945,
  "timestamp": "2026-10-10T12:00:00.120000+00:00",
  "metadata": {
    "model_version": "RandomForest_v1.0",
    "raw_shade": "Medium",
    "data_source": "SIMULATED"
  }
}
```

---

## 5. Decision Validation & Safety Gate Specifications

Before any mechanical diverter movement is executed, the Decision Validator checks the incoming decision against 8 mandatory safety rules:

1. **Message Well-Formedness:** Valid JSON dictionary with required fields (`type="decision"`, non-empty `request_id`, valid ISO 8601 `timestamp`, valid string `label`).
2. **Request ID Matching:** `request_id` in response must exactly match the originating measurement request ID.
3. **Replay & Duplicate Protection:** Once a `request_id` is processed, duplicate responses with the same ID are immediately rejected (`ERR_DUPLICATE_RESPONSE`).
4. **Timestamp Freshness & Monotonicity:**
   - Response timestamp must not predate the request timestamp (`ERR_CLOCK_SKEW_PREDATED`).
   - Response timestamp must not be future-dated beyond clock drift allowance ($\le 0.5\text{ s}$, `ERR_FUTURE_DATED_TIMESTAMP`).
5. **Response Latency Timeout:**
   - Maximum allowable elapsed time between request dispatch and response evaluation is **$2.0\text{ seconds}$**.
   - Responses arriving $> 2.0\text{ s}$ are rejected (`ERR_RESPONSE_EXPIRED`), triggering a safe `HOLD`.
6. **Label Whitelist:** Label must belong to the approved set `{"BIN_A", "BIN_B", "BIN_C", "HOLD", "REJECT_UNKNOWN"}` (`ERR_UNSUPPORTED_LABEL`).
7. **Confidence Policy:** When confidence score is present, it must be $\ge 0.60$ (`ERR_LOW_CONFIDENCE`).
8. **Actuator Safe Neutral Return:** On any rejection or `HOLD`, the diverter moves to $90.0^\circ$ (Home Position) and logs `ActuatorEvent(status="REJECTED"|"HELD")`.

---

## 6. Diverter Actuator PWM Timing (SG90 Servo)

| Servo Position | Diverter Angle | Target Pulse Width (50 Hz / 20 ms Period) |
|---|---|---|
| Full Left (Bin A) | $45.0^\circ$ | $1.000\text{ ms}$ |
| Center / Home (Bin B / Hold) | $90.0^\circ$ | $1.500\text{ ms}$ |
| Full Right (Bin C) | $135.0^\circ$ | $2.000\text{ ms}$ |
| Reject Chute | $180.0^\circ$ | $2.500\text{ ms}$ |

---

## 7. Educational & Prototype Disclaimer

This prototype classifies grain/seed optical surface reflectance shade only. It does **not** test for food safety, chemical purity, grain grade, nutritional content, or seed viability.


## Authoritative Serial Protocol (software prototype)

The serial framing format is **NDJSON (JSON Lines)**, not comma-separated values. One UTF-8 JSON object is sent per line, terminated by `\n`. `application/serial_reader.py` parses only this format.

Example measurement line:

```json
{"type":"measurement","request_id":"REQ-001","data_source":"simulated","sample_LDR":1200,"ambient_LDR":800,"reference_value":900,"timestamp":"2026-10-10T14:32:00+00:00"}
```

The parser also accepts these sensor fields under a `features` object. Required fields are `type="measurement"`, non-empty `request_id`, `sample_LDR`, and `ambient_LDR`; `reference_value` is optional. Values must be finite numbers. The application performs ADC range and ambient-value validation before inference. Empty reads are treated as serial timeouts; malformed messages are reported and skipped; serial I/O exceptions are reported as communication failures.

## Model and action contract

Model feature order: `sample_LDR`, `ambient_LDR`, `reflectance_ratio`. Formula: `reflectance_ratio = sample_LDR / ambient_LDR`; ambient must be greater than zero. Class-to-bin proposal: `Dark -> BIN_A`, `Medium -> BIN_B`, `Light -> BIN_C`. A low-confidence, invalid, unsupported, or expired decision must resolve to `HOLD` according to the configured validator policy.

**Pending team approval:** the class-to-physical-bin orientation, confidence threshold, full serial request/response exchange, and exact timestamp ownership must be confirmed by the team before physical actuation. The current serial bridge receives measurements only; it does not yet transmit decision responses to the MCU.
