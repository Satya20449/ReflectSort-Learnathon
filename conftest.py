"""
Pytest configuration and pythonpath initialization for ReflectSort.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
M4_ROOT = ROOT / "member4_system"
M4_SRC = M4_ROOT / "src"
M4_EXAMPLES = M4_ROOT / "examples"

for p in [str(ROOT), str(M4_ROOT), str(M4_SRC), str(M4_EXAMPLES)]:
    if p not in sys.path:
        sys.path.insert(0, p)
