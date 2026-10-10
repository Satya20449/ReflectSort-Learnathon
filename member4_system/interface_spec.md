# ReflectSort — Inter-Module Interface Specification

**Project:** ReflectSort — Sensor-Based Seed/Grain Shade Classification and Sorting Prototype  
**Course:** Machine Learning – Embedded Systems Design (ML–ESD)  
**Project Variant:** PROJECT-12-VARIANT-06 | **Team:** ML-ESD-TEAM-117  
**Author:** Ajitesh Karan (2500032236) — Member 4 (System Architecture, Hardware Planning & Simulation)  
**Document Status:** Inter-Member Contract Specification (Pending Final Team Sign-off)  

---

## 1. Team Ownership & Responsibilities

| Member | Roll Number | Primary Responsibility | Interface Ownership |
| :--- | :--- | :--- | :--- |
| **Satya Nayak** | 2500030899 | Team Lead & System Integration | End-to-end integration, Git repository management, merge approvals |
| **Kuldeep Singh** | 2500031372 | Machine Learning & Dataset | Labeled dataset curation, model training, feature selection & ordering, inference pipeline |
| **Satyam Rai** | 2500032600 | Python Application & UI | Host-side UI/CLI dashboard, serial communication orchestration, prediction display |
| **Ajitesh Karan** | 2500032236 | System Design, Simulation & Hardware Planning | Data schemas, sensor/actuator simulation, decision validation safety gate, firmware specification, test suite |

---

## 2. Sensor-to-Model Interface (Ajitesh ↔ Kuldeep ↔ Satyam)

This interface defines how optical sensor measurements acquired from the sensing chamber are formatted for ingestion into Kuldeep's Machine Learning classifier.

### 2.1 Proposed Feature Vector

The sensor layer computes and packages the following numerical features:

| Feature Key | Type | Representation / Units | Range | Description |
| :--- | :--- | :--- | :--- | :--- |
| `sample_LDR` | `float` | 12-bit ADC digital counts | `[0.0, 4095.0]` | Reflected light intensity from grain surface ($V = \text{counts} \times 3.3 / 4095$) |
| `ambient_LDR` | `float` | 12-bit ADC digital counts | `[0.0, 4095.0]` | Background ambient light level measured in the chamber |
| `reference_value` | `float` | 12-bit ADC digital counts | `[0.0, 4095.0]` | Calibrated baseline reading from standard white/neutral reference |
| `differential_LDR` | `float` | Derived ADC counts | `[-4095.0, 4095.0]` | `sample_LDR - ambient_LDR` (background-subtracted optical reflection) |
| `contrast_ratio` | `float` | Unitless normalized ratio | `[-1.0, 2.0]` | `(sample_LDR - ambient_LDR) / reference_value` (safe for ref $\approx 0$) |
| `ambient_ratio` | `float` | Unitless ratio | `[0.0, 100.0]` | `sample_LDR / max(ambient_LDR, 1e-6)` |

> [!IMPORTANT]
> **Action Item for Kuldeep Singh (ML Member):**  
> Kuldeep must review and formally confirm the exact subset and order of features expected by his trained model pipeline (e.g. numpy array shape `(1, N)` or named dictionary) before final host integration. Member 4 does NOT modify Kuldeep's model or invent his final feature order.

### 2.2 Data Integrity & Numerical Safety Rules
1. **Strict Type Safety:** Non-numeric values, strings, `None`, booleans, `NaN`, and infinities (`+inf`, `-inf`) are strictly rejected with an explicit `InvalidNumericValueError`.
2. **Zero-Division Protection:** The schema computes `contrast_ratio` and `ambient_ratio` with explicit numerical epsilon guards (`NUMERICAL_EPSILON = 1e-6`), guaranteeing finite, non-overflowing numbers.
3. **No Silent Fabrication:** Corrupted or out-of-range sensor readings are never silently clamped or interpolated. They are flagged as errors to prevent unsafe actuation.
4. **Simulation Tagging:** All software-generated records MUST have `data_source="simulated"`. The simulator will raise a `ValidationError` if an attempt is made to label simulated data as physically measured.

---

## 3. Host-to-Controller Protocol (Satyam ↔ Ajitesh)

Communication between the Python host application (Satyam) and the microcontroller/firmware simulator (Ajitesh) uses a **JSON-Lines (NDJSON)** framing format over USB virtual serial (or direct memory in software simulation mode).

### 3.1 Measurement Request (Controller / Simulator → Host)

Dispatched by the microcontroller when a specimen is positioned in the optical chamber:

```json
{"type":"measurement","request_id":"REQ-GRAIN-00104","data_source":"simulated","features":{"sample_LDR":3210.5,"ambient_LDR":852.1,"reference_value":2400.0,"differential_LDR":2358.4,"contrast_ratio":0.9827,"ambient_ratio":3.7677},"timestamp":"2026-10-10T14:32:00.125000+00:00","metadata":{"run_id":"RUN-2026-A","sample_position":"tray_center","LED_setting":"WHITE_100PCT"}}
```

### 3.2 Classification Decision (Host → Controller / Simulator)

Returned by the host Python application after running inference through Kuldeep's model:

```json
{"type":"decision","request_id":"REQ-GRAIN-00104","label":"BIN_A","confidence":0.962,"timestamp":"2026-10-10T14:32:00.245000+00:00","metadata":{"model_version":"v1.0.0_rf_shade_classifier","inference_time_ms":18.5}}
```

---

## 4. Permitted Classification Labels & Diverter Actions

The embedded safety validator strictly checks labels against the permitted whitelist:

| Label | Description | Default Diverter Target Angle | Default Pulse Width | Fallback if Unsure |
| :--- | :--- | :--- | :--- | :--- |
| `BIN_A` | High surface reflectance (e.g. Light Shade grain) | `45.0°` | `1.250 ms` | `HOLD` |
| `BIN_B` | Moderate surface reflectance (e.g. Medium Shade grain) | `90.0°` | `1.500 ms` | `HOLD` |
| `BIN_C` | Low surface reflectance (e.g. Dark/Discolored grain) | `135.0°` | `1.750 ms` | `HOLD` |
| `REJECT_UNKNOWN` | Foreign object, non-grain, or ambiguous specimen | `165.0°` (Reject Chute) | `1.917 ms` | `HOLD` |
| `HOLD` | Safety hold / neutral state / no mechanical actuation | `90.0°` (Neutral Home) | `1.500 ms` | `HOLD` |

> [!WARNING]
> Any label received outside this set (e.g., `"BIN_D"`, `"SHADE_4"`, or arbitrary text) is rejected with error code `ERR_UNSUPPORTED_LABEL` and automatically forced to `HOLD`.

---

## 5. Safety Validation & Timing Constraints

The `DecisionValidator` module enforces the following strict invariant checks:

1. **Request ID Correlation:** `response.request_id` MUST match the active `expected_request_id`. Mismatches trigger `ERR_REQUEST_ID_MISMATCH` to prevent stale race conditions.
2. **Replay Protection:** Replayed responses with previously processed `request_id`s are blocked with `ERR_DUPLICATE_RESPONSE`.
3. **Response Latency / Expiry Gate:** The maximum allowed time window from measurement dispatch to decision receipt is **2.0 seconds** (`max_response_latency_seconds = 2.0`). Stale decisions trigger `ERR_RESPONSE_EXPIRED`.
4. **Temporal Monotonicity & Clock Drift:**
   - Responses timestamped before the request timestamp trigger `ERR_CLOCK_SKEW_PREDATED`.
   - Responses future-dated by $> 0.50\,\text{s}$ trigger `ERR_FUTURE_DATED_TIMESTAMP`.
5. **Confidence Gating (Configurable):** If confidence gating is enabled, inferences below `min_confidence_threshold` trigger `ERR_LOW_CONFIDENCE`. If `require_confidence = True`, missing confidence scores trigger `ERR_MISSING_CONFIDENCE`.
6. **Fail-Safe Default:** On ANY validation failure, the actuator simulator enters the neutral `SAFETY_BLOCKED_HOME` state ($90.0^\circ$) and blocks diverter movement.

---

## 6. Integration Checklist for Teammates

- [ ] **Satya (Integration Lead):** Confirm JSON-Lines framing and serial port baud rate (115200 baud, 8N1).
- [ ] **Kuldeep (ML Lead):** Verify feature keys in `SensorRecord.to_model_features()` and specify final model input vector format.
- [ ] **Satyam (App Lead):** Implement async serial reader with request/response ID matching matching `DecisionRequest`/`DecisionResponse` schemas.
- [ ] **Ajitesh (Member 4):** Provide simulation fixtures and test harness for team integration testing prior to hardware availability.
