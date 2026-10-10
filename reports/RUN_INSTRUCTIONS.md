# ReflectSort Run Instructions (Windows PowerShell)

Run commands from the `ReflectSort_GitHub_Integration` project root.

## 1. Activate the existing Python environment

```powershell
.\.venv\Scripts\Activate.ps1
```

If you have not created the environment yet:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e ".[dev]"
```

## 2. Run diagnostics

```powershell
python .\application\shade_demo.py --check
```

## 3. Run tests

```powershell
python -m pytest -q
```

The latest verified test run passed all 102 tests. Run the tests again after changing files.

## 4. Run the software demonstration

Use the commands and arguments supported by the installed application:

```powershell
python .\application\shade_demo.py --help
```

## 5. Serial bridge (optional)

The serial bridge has been tested with mocked serial input only. Actual board and firmware validation is still pending. If testing on Windows, use the COM port assigned to your board, for example:

```powershell
python .\application\serial_reader.py COM3 --baud 115200 --timeout 2
```

Replace `COM3` with the correct port. Confirm the actual script arguments with `--help` before use.

## 6. Hardware status

The current verification covers software and simulation. Physical STM32, LDR sensor, and servo behavior has not been validated on assembled hardware. Do not interpret simulated results as real-world hardware performance.