# ReflectSort — STM32 NUCLEO-F446RE Hardware Architecture & Engineering Plan

**Project:** ReflectSort — Sensor-Based Seed/Grain Shade Classification and Sorting Prototype  
**Course:** Machine Learning – Embedded Systems Design (ML–ESD)  
**Project Variant:** PROJECT-12-VARIANT-06 | **Team:** ML-ESD-TEAM-117  
**Author:** Ajitesh Karan (2500032236) — Member 4 (System Design & Hardware Planning)  
**Hardware Status:** Planning & Design Phase (Physical components not currently available in workspace)  

---

## 1. System Overview & Selected Microcontroller

The ReflectSort embedded hardware prototype is architected around the **STMicroelectronics NUCLEO-F446RE** development board (LQFP64 package).

### 1.1 Microcontroller Specifications (STM32F446RE)
- **Core:** ARM® 32-bit Cortex®-M4 with FPU, adaptive real-time accelerator (ART Accelerator™) running at up to 180 MHz.
- **Memory:** 512 KB Flash memory, 128 KB SRAM.
- **Analog Peripherals:** 3× 12-bit, 2.4 MSPS Analog-to-Digital Converters (ADCs) with up to 16 channels, configurable sampling times, and DMA support.
- **Timers:** Up to 17 timers (including TIM2, TIM3, TIM4 16/32-bit general-purpose timers for high-resolution PWM generation).
- **Communication:** Up to 4× USARTs / 2× UARTs, 4× SPI, 3× I2C, USB 2.0 full-speed device/host/OTG.
- **Development Interface:** Integrated ST-LINK/V2-1 debugger with Virtual COM Port (VCP) over USB.

---

## 2. Bill of Materials & Component Roles

```
                                +-----------------------------+
                                |  Host Computer (Python 3)   |
                                +--------------+--------------+
                                               | USB VCP Serial (115200)
                                +--------------v--------------+
  +---------------------------> |  STM32 NUCLEO-F446RE Board  | <---------------------------+
  |                             +--------------+--------------+                             |
  | Analog Voltage 0-3.3V (PA0)                | PWM 50Hz (PA6)   Analog Voltage 0-3.3V (PA1) |
  |                                            |                                            |
+-+----------------------+      +--------------v--------------+      +----------------------+--+
| Sample LDR + Divider   |      | Micro Servo Motor (MG90S)   |      | Ambient LDR + Divider   |
| (Optical Chamber Refl) |      | (Angular Diverter Gate)     |      | (Background Light Ref)  |
+------------------------+      +--------------+--------------+      +-------------------------+
                                               | Mechanical Flap
                                +--------------v--------------+
                                |  Sorting Bins: A, B, C, Rej |
                                +-----------------------------+
```

| Component | Part / Spec | Role in ReflectSort | Power Rail |
| :--- | :--- | :--- | :--- |
| **Microcontroller** | NUCLEO-F446RE | Sensor sampling (12-bit ADC), signal filtering, UART host bridge, PWM servo timing, safety validation | +5V (USB Powered) / +3.3V Internal VDD |
| **Sample LDR Sensor** | GL5528 (5-10kΩ light / 0.5MΩ dark) | Measures reflected diffuse light from seed/grain sample under active LED illumination | +3.3V Analog (AVDD) |
| **Ambient/Reference LDR** | GL5528 matched pair | Measures ambient chamber background light and white standard reference tile | +3.3V Analog (AVDD) |
| **Illumination Source** | High-CRI 5mm White Diffused LED | Provides consistent, localized optical illumination inside the sensing tunnel | +5V external or GPIO driven via transistor switch |
| **Actuator Diverter** | TowerPro SG90 / MG90S Micro Servo | Drives mechanical deflection gate to direct falling/slotted grain into destination chutes | +5V Regulated External DC Supply |
| **External Power Supply** | 5V / 2.0A DC Regulated Adapter | Powers servo motor and LED to prevent microcontroller brownout resets from motor stall currents | +5V External Rail |
| **Passive Pass-Throughs** | 10kΩ 1% Metal Film Resistors, 100nF ceramic decoupling caps, 150Ω LED ballast | Voltage dividers, signal filtering, current limiting | Circuit Boards / Breadboard |

---

## 3. Circuit Schematics & Electrical Interfacing

### 3.1 LDR Sensor Voltage Divider Topology

The LDR resistance $R_{\text{LDR}}$ decreases with increasing luminous flux. To obtain an analog voltage that scales with surface reflectance, the LDR is placed on the high side of a precision voltage divider:

$$V_{\text{ADC}} = V_{\text{DD}} \times \frac{R_{\text{fixed}}}{R_{\text{LDR}} + R_{\text{fixed}}}$$

```
   +3.3V (AVDD)
       |
     [ LDR ]  (GL5528 Photoresistor)
       |
       +------> Analog Input (PA0 / PA1) ---> 12-bit ADC (STM32)
       |
     [ R_f ]  (10 kΩ, 1% Metal Film Precision Resistor)
       |
      ---
      GND
```

- **ADC Conversion Formula:** Digital counts $0 \dots 4095$ correspond to $0.0\,\text{V} \dots 3.3\,\text{V}$:
  $$V_{\text{in}} = \frac{\text{ADC Counts}}{4095.0} \times 3.30\,\text{V}$$
- **Anti-Aliasing Filter:** Optional $100\,\text{nF}$ ceramic capacitor placed in parallel with $R_{\text{fixed}}$ to filter out high-frequency optical flicker and electrical noise.

### 3.2 LED Illuminator Circuit

```
   +5V Ext
       |
     [ R_limit ] (150 Ω, 0.25 W)
       |
     ( LED )     (White 5mm High-CRI Diffused LED, Vf ≈ 3.2V, If ≈ 12mA)
       |
     | /  Collector
   --|    NPN Transistor (2N2222 / 2N3904)
     | \  Emitter
       |
      ---
      GND
```
- **Base Control:** STM32 GPIO (e.g. PB0) via $1\,\text{k}\Omega$ base resistor allows the firmware to enable illumination strictly during active sampling, minimizing sensor self-heating.

### 3.3 Servo Motor Actuator Interfacing

```
   +5V External Supply  -----> Servo V+ (Red Wire)
   External Supply GND  -----> Servo GND (Brown/Black Wire) <---+ (Common Ground)
   STM32 Board GND      ----------------------------------------+
   STM32 TIM3_CH1 (PA6) -----> Servo PWM Signal (Orange/Yellow Wire)
```

- **PWM Frequency:** $50\,\text{Hz}$ ($20.0\,\text{ms}$ period).
- **Preliminary Uncalibrated Pulse Width Mapping (Subject to Rig Calibration):**
  - $1.00\,\text{ms}$ ($5.00\%$ duty) $\rightarrow 0^\circ$ (Minimum physical travel limit)
  - $1.25\,\text{ms}$ ($6.25\%$ duty) $\rightarrow 45^\circ$ (`BIN_A` — Light Shade default)
  - $1.50\,\text{ms}$ ($7.50\%$ duty) $\rightarrow 90^\circ$ (`BIN_B` / Neutral Home `HOLD` default)
  - $1.75\,\text{ms}$ ($8.75\%$ duty) $\rightarrow 135^\circ$ (`BIN_C` — Dark Shade default)
  - $1.92\,\text{ms}$ ($9.60\%$ duty) $\rightarrow 165^\circ$ (`REJECT_UNKNOWN` — Reject Chute default)

---

## 4. STM32F446RE Pin Allocation & Peripheral Mapping

> [!IMPORTANT]
> The following table has been cross-verified against official ST documentation:
> - **STM32F446xE Datasheet (DS10693)**
> - **STM32F446xx Reference Manual (RM0390)**
> - **STM32 Nucleo-64 Boards User Manual (UM1724)**

| Pin Label | STM32 GPIO | Morpho / Arduino Header | Peripheral Function | Alternate Function (AF) | Connected Hardware / Role | Potential Pin Conflicts & Cautions |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **A0** | `PA0` | CN8 Pin 1 / CN7 Pin 28 | `ADC1_IN0` | Analog (AF0) | Sample LDR Divider | Shared with `TIM2_CH1`/`TIM5_CH1`; keep in Analog mode to disable digital input buffers. |
| **A1** | `PA1` | CN8 Pin 2 / CN7 Pin 30 | `ADC1_IN1` | Analog (AF0) | Ambient / Reference LDR Divider | Shared with `TIM2_CH2`/`TIM5_CH2`; keep in Analog mode. |
| **D12** | `PA6` | CN9 Pin 5 / CN7 Pin 12 | `TIM3_CH1` (PWM Out) | `AF2` (`TIM3_CH1`) | Servo Motor PWM Signal (Option 1) | Shared with `SPI1_MISO` and `ADC1_IN6`. Ensure SPI1 is unused or remapped. |
| **D9** | `PC7` | CN9 Pin 3 / CN7 Pin 19 | `TIM3_CH2` (PWM Out) | `AF2` (`TIM3_CH2`) | Servo Motor PWM Signal (Option 2) | Alternative 50Hz PWM output channel on Timer 3. |
| **D3** | `PB0` | CN9 Pin 4 / CN10 Pin 34 | `GPIO_Output` | Push-Pull (AF0) | LED Transistor Driver Base | Driving transistor base through 1kΩ resistor. |
| **LD2** | `PA5` | On-board / CN9 Pin 6 | `GPIO_Output` | Push-Pull | On-board Green Status LED | Connected directly to Green LED LD2. Avoid connecting heavy external loads to D13. |
| **B1** | `PC13` | On-board / CN7 Pin 23 | `GPIO_Input` (EXTI13) | Input Pull-up | User Pushbutton | Active-LOW user button; used for manual acquisition trigger or fault reset. |
| **USART2_TX** | `PA2` | Connected to ST-LINK | `USART2_TX` | `AF7` (`USART2`) | USB Virtual COM Port (115200 baud) | Connected to ST-LINK VCP via solder bridge `SB62` (closed by default). |
| **USART2_RX** | `PA3` | Connected to ST-LINK | `USART2_RX` | `AF7` (`USART2`) | USB Virtual COM Port (115200 baud) | Connected to ST-LINK VCP via solder bridge `SB63` (closed by default). |
| **+3V3** | `VDD` | CN6 Pin 4 / CN7 Pin 16 | `3.3V Analog Power` | Power | LDR Pull-up Reference Rail | Clean analog VDD rail. Do NOT power servo motor from this pin. |
| **GND** | `GND` | CN6 Pin 6,7 / CN7 Pin 20 | `System Ground` | Ground | Common Ground Bus | Must be tied to external 5V power supply ground. |

---

## 5. Mandatory Pre-Assembly Electrical Verification Checklist

Prior to applying power or mounting physical components to the NUCLEO board, the following laboratory tests must be performed:

1. **ADC Voltage Clamping Check (HW-ELEC-01):** Use a digital multimeter (DMM) to measure divider output voltage under maximum illumination. Ensure $V_{\text{ADC}} \le 3.30\,\text{V}$ under all conditions to prevent microcontroller GPIO damage.
2. **Servo Power Supply Isolation (HW-ELEC-02):** Verify that the servo $+5\,\text{V}$ pin is powered strictly from the external power supply and NOT from the NUCLEO board's on-board $3.3\,\text{V}$ or $5\,\text{V}$ regulator.
3. **Common Ground Verification:** Confirm continuity between external $5\,\text{V}$ ground and NUCLEO `GND` pins with a DMM ($R < 0.2\,\Omega$).
4. **Current Limiting Verification:** Measure LED forward current with a multimeter in series. Verify $I_{\text{LED}} \le 20\,\text{mA}$.
5. **Servo Mechanical Clearance Check:** Manually rotate the diverter arm to confirm that $0^\circ$ to $180^\circ$ rotation is completely free of mechanical interference or chute obstruction.
6. **Failsafe Neutral Check:** Confirm that upon power interruption or disconnected PWM signal, the diverter remains in or falls to a safe neutral position without jamming the grain feed path.
