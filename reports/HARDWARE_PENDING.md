# ReflectSort — Hardware Status and Pending Work

**Project:** PROJECT-12-VARIANT-06  
**Status:** Software-first integrated prototype; physical hardware implementation and validation are not complete.

## 1. What is implemented in software

- ML model loading and classification using the supplied project model artifact.
- Manual/CLI and CSV reading paths.
- Simulated sensor readings, derived features, decision validation, timeout and replay checks.
- Simulated actuator decisions and automated software tests.
- An NDJSON serial-reader implementation with mock tests; this verifies parser/bridge behavior in software only.

These are software behaviors. They do not prove real sensor accuracy, physical serial communication, electrical correctness, PWM waveform quality, or mechanical sorting.

## 2. Hardware availability status

The user previously reported having access to an STM32 NUCLEO-F446RE board, an LDR sensor module, an LED, an SG90 servo, a breadboard, and jumper wires. This is user-reported availability only; the components have not been independently inspected or tested as part of this software package. External servo power supply availability has not been verified.

No physical hardware implementation or validation is claimed as completed.

## 3. Future hardware tasks

- Inspect exact board, sensor-module pin labels, LED/resistor, servo model/wiring, and suitable external servo supply.
- Confirm STM32CubeMX clock, ADC, timer/PWM, and UART configuration for the actual board and firmware.
- Validate ADC voltage limits and sensor readings using safe test procedures.
- Calibrate LED illumination, sensor placement, dark/white references, and optical shielding.
- Implement and verify the embedded NDJSON parser and request/response behavior at the agreed baud rate.
- Measure UART reliability, PWM frequency/pulse widths, servo power stability, and servo travel.
- Confirm mechanical bin mapping and safe HOLD/timeout behavior with the actual mechanism.
- Collect clearly labelled physical measurements and evaluate the model on them before making real-world performance claims.

## 4. Approval items before physical integration

- Team approval of `Dark -> BIN_A`, `Medium -> BIN_B`, `Light -> BIN_C` physical orientation.
- Team approval of confidence threshold and HOLD policy.
- Confirmation of the complete serial request/response schema and which side owns each timestamp.
- Confirmation of external servo power arrangements and actual pin assignments.

Until these checks are performed, all hardware-specific results must be marked **not tested**.
