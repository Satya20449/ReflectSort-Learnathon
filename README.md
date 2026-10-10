# ReflectSort-Learnathon
Seed/Grain Shade Prototype using sensors, machine learning, and STM32

# ReflectSort — Explainable Optical Mini-Sorting Cell

**Project:** Seed/Grain Shade Prototype  
**Project ID:** PROJECT-12-VARIANT-06  
**Team:** 4 Members  
**Development Environment:** STM32CubeMX, STM32CubeIDE, Python, PyCharm, Git and GitHub  
**Current Development Mode:** Software-first; hardware availability to be confirmed

---

## 1. Project Overview

ReflectSort is a mini optical sorting prototype designed to classify clean seed or grain samples into broad shade groups using reflected-light measurements.

The system is intended to combine optical sensing, embedded control, machine learning and a simple sorting mechanism. If a sample cannot be classified confidently, the system should hold it for review rather than automatically assigning an uncertain category.

The project will be developed incrementally, beginning with software and system design. The implementation will be adapted to the hardware actually provided during the Learnathon.

**Important:** Shade classification is the scope of this prototype. The system does not claim to determine seed quality, freshness, purity, nutritional value or food safety.

## 2. Problem Statement

Manual sorting of seeds or grains by visible shade can be inconsistent. Lighting conditions, sample positioning and differences in reflected light may affect how samples are classified.

We aim to develop a small, explainable prototype that measures reflected light under controlled conditions and classifies samples into predefined shade groups, with a mechanism for handling uncertain predictions.

## 3. Proposed Solution

The proposed system will:

1. Illuminate a sample using a white LED.
2. Measure reflected light using an LDR-based sensor arrangement.
3. Read and process sensor measurements using a compatible microcontroller, if hardware is available.
4. Pass suitable measurements to a machine-learning classifier.
5. Produce one of four outputs: `BIN_A`, `BIN_B`, `BIN_C` or `HOLD`.
6. Use a servo-controlled flap or another permitted mechanism to direct samples to collection bins if the physical sorting mechanism can be implemented.

If hardware is unavailable, the team will develop a software demonstration using clearly labelled sample or simulated inputs. Such a demonstration will not be represented as a physically tested sorting machine.

## 4. System Architecture

### 4.1 Proposed Hardware Flow

Sample → Controlled LED illumination → LDR sensor readings → STM32 microcontroller → Measurement processing and classification interface → Sorting decision → Servo mechanism → Collection bin or HOLD.

The precise division of processing between the microcontroller and Python application will be determined during implementation and according to the Learnathon requirements.

### 4.2 Software-First Flow

Sample or simulated readings → Data preparation → Machine-learning model → Predicted category → Python demonstration → Result and test logging.

The software-first flow allows development to proceed while the availability of physical components is uncertain.

## 5. Components and Tools

### Hardware — subject to availability

- STM32 NUCLEO-H753ZI or another permitted board, potentially NUCLEO-F446RE.
- LDR sensor or sensors and suitable voltage-divider components.
- White LED and appropriate current-limiting resistor.
- Servo motor and compatible power supply.
- Connecting wires, sample tray and a light-shielding enclosure or optical tunnel.
- Clean, safe seed/grain samples or permitted inert replicas.
- Collection bins or a simple sorting guide.

The final component list, pin mapping, power requirements and firmware configuration must be verified against the board and components actually provided.

### Software

- STM32CubeMX — microcontroller peripheral and pin configuration.
- STM32CubeIDE — embedded C development and firmware build.
- Python and PyCharm — data preparation, ML development and the demonstration application.
- pandas and NumPy — data processing.
- scikit-learn — machine-learning model development.
- matplotlib — visualisation of measurements and test results.
- Git and GitHub — version control, collaboration and project documentation.

Exact library versions and additional dependencies will be documented when implementation begins.

## 6. Shade Categories and Data Format

The prototype will use the following output labels:

| Label | Meaning |
|---|---|
| `BIN_A` | First configured shade group |
| `BIN_B` | Second configured shade group |
| `BIN_C` | Third configured shade group |
| `HOLD` | Uncertain, invalid or unsupported input requiring review |

The precise shade boundaries will be established from suitable labelled samples and sensor calibration. The labels must not be assumed to represent fixed brightness ranges until these have been defined and tested.

### Proposed dataset fields

- `sample_id` — unique sample identifier.
- `ldr_reading_1` — reading from the first sensor, if available.
- `ldr_reading_2` — reading from the second sensor, if available.
- `reference_reading` — ambient-light reference, if implemented.
- `shade_label` — verified category assigned to the sample.

The final schema may change depending on the available sensors. Simulated measurements must be explicitly labelled as simulated and kept distinguishable from genuine sensor measurements.

## 7. Team Responsibilities

### Member 1 — Team Lead and Integration

**Primary responsibility:** Coordinate the project and integrate the work of all members.

Tasks:
- Maintain the shared GitHub repository and project structure.
- Track progress, dependencies, issues and review deadlines.
- Coordinate interfaces between the ML model, Python application and embedded design.
- Review code integration and ensure the application can be run reproducibly.
- Maintain project documentation and record verified implementation status.
- Prepare review evidence, presentation materials and the final demonstration.
- Coordinate testing and help resolve integration problems.

Deliverables:
- Shared repository and project documentation.
- Integration checklist and progress tracking.
- Tested combined demonstration, where feasible.
- Review and final presentation materials.

### Member 2 — Machine Learning and Data

**Primary responsibility:** Develop and evaluate the shade-classification model.

Tasks:
- Define and document the dataset format.
- Collect genuine readings if sensors are available; otherwise prepare clearly labelled sample or simulated data.
- Clean and prepare the dataset.
- Train a suitable baseline classifier using scikit-learn.
- Evaluate it using held-out test data and suitable metrics.
- Investigate confidence handling and the `HOLD` decision.
- Document the model's limitations and instructions for use.

Deliverables:
- Dataset and its description.
- Training script.
- Saved model, if model persistence is used.
- Evaluation results and instructions for integrating the model.

### Member 3 — Python Application and Demonstration

**Primary responsibility:** Build the software interface that displays shade predictions.

Tasks:
- Create a simple command-line or graphical demonstration.
- Accept supported sensor measurements or clearly labelled simulated inputs.
- Load and use Member 2's model.
- Validate input values and handle invalid or unsupported inputs.
- Display the predicted category and a useful explanation of the result.
- Record demonstration results and document how to run the application.
- Coordinate changes to the model interface with Member 2.

Deliverables:
- Python application.
- Dependency list and run instructions.
- Demonstration examples and screenshots.
- Input-validation and error-handling evidence.

### Member 4 — Embedded System and Hardware Design

**Primary responsibility:** Design the sensor interface and proposed embedded control.

Tasks:
- Document the system block diagram and expected data flow.
- Inspect the actual board and components when provided.
- Plan the LDR input circuit, LED control and servo interface.
- Configure supported peripherals using STM32CubeMX.
- Develop or prepare firmware in STM32CubeIDE.
- Document board-specific pin mapping, voltage limits and power requirements.
- Verify hardware behaviour only when the required physical components are available.
- Coordinate the embedded measurement format with Members 2 and 3.

Deliverables:
- System architecture and hardware block diagram.
- Proposed wiring and pin-mapping documentation.
- Firmware source and build instructions, if implemented.
- Hardware test results or a documented list of unverified hardware functions.

## 8. Collaboration and GitHub Workflow

All members will collaborate through the shared repository:

https://github.com/Satya20449/ReflectSort-Learnathon

### Working rules

1. Accept the repository invitation before attempting to contribute.
2. Clone the repository once on each member's laptop.
3. Pull the latest changes before starting a new task.
4. Work primarily on files assigned to your role.
5. Check changes using `git status`.
6. Stage and commit changes with clear messages.
7. Push commits to the agreed branch or create a feature branch and pull request when the team uses that workflow.
8. Communicate before modifying shared files or changing interfaces.
9. Never commit passwords, access tokens or private credentials.

### Common Git commands

```bash
git pull origin main
git status
git add <your-file-or-folder>
git commit -m "Describe your change"
git push
```

New contributors should follow the repository's current branch policy and avoid force-pushing shared branches.

## 9. Project Folder Structure

```text
ReflectSort_Learnathon/
├── README.md
├── docs/
│   ├── architecture.md
│   ├── requirements.md
│   └── test-plan.md
├── ml-model/
│   ├── data/
│   ├── train_model.py
│   └── model-evaluation.md
├── python-demo/
│   ├── app.py
│   └── requirements.txt
├── stm32-firmware/
│   ├── Core/
│   ├── Drivers/
│   └── README.md
├── tests/
│   ├── test-cases.md
│   └── results/
└── presentation/
    ├── review-evidence/
    └── final-presentation/
```

This is the intended organisation. Files and subfolders will be added as work is implemented; empty directories are not stored by Git.

## 10. Testing and Validation Plan

The team intends to verify the following:

- Input data has the expected format and contains valid values.
- The ML model produces the documented category labels.
- The `HOLD` path handles uncertain or invalid predictions appropriately.
- The Python application loads the correct model and displays results.
- The embedded firmware builds successfully for the actual target board.
- Sensor readings are repeatable under controlled lighting.
- The physical sorting mechanism directs samples to the intended destination, if hardware is available.
- Results distinguish simulated tests from real sensor and hardware tests.

Metrics, thresholds and acceptance criteria will be finalised when the dataset, model and hardware configuration are known.

## 11. Implementation Status

The status below reflects the project setup documented at the start of implementation. Update it only when the corresponding work has actually been completed and verified.

| Item | Status |
|---|---|
| GitHub repository created | Completed |
| Local Git repository connected to GitHub | Completed |
| Initial project folders created | Completed |
| Four-member responsibilities defined | Planned and assigned |
| Hardware availability confirmed | Pending |
| Dataset created and verified | Pending |
| ML model trained and evaluated | Pending |
| Python application implemented | Pending |
| STM32 firmware configured and built | Pending |
| Physical sorting mechanism tested | Pending |
| Integrated end-to-end demonstration | Pending |
| Review evidence and final presentation | Pending |

## 12. Known Constraints and Risks

- Hardware availability and the final STM32 board model are not yet confirmed.
- Firmware and pin assignments may require adaptation to the supplied board.
- LDR readings depend on lighting, geometry, sensor characteristics and calibration.
- Simulated measurements cannot establish physical sensor accuracy.
- A model trained on synthetic or insufficiently representative data may not generalise to real samples.
- The prototype classifies shade only and must not make unsupported agricultural quality or safety claims.
- Uncertain predictions should be held for review rather than forced into a shade group.

## 13. Learnathon Milestones

The planned Learnathon window is 6:00 PM to 12:00 PM the following day. The exact number and timing of reviews must follow the organisers' instructions.

The team will prioritise:

1. Confirm requirements, available components and review criteria.
2. Finalise the architecture and shared input/output format.
3. Develop the ML model and Python demonstration in parallel.
4. Prepare the embedded design and adapt to the available board.
5. Integrate, test and document the implementation.
6. Present verified results, limitations and future improvements.

## 14. Future Improvements

Potential future work includes:
- Calibrating measurements with real samples.
- Improving shade-group separation and uncertainty handling.
- Integrating the embedded controller with the software pipeline.
- Testing the physical sorting mechanism.
- Adding reproducible data collection and result logging.
- Improving enclosure design and sample positioning.

## 15. Team and Acknowledgements

This project is developed by a four-member team as part of the ReflectSort Seed/Grain Shade Prototype Learnathon.

Individual names, GitHub handles, and completed contributions should be added after the team confirms them.

---

**Project principle:** Build incrementally, test honestly, document clearly, and adapt the implementation to the actual requirements and available components.
