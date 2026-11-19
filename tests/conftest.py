import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in ("src/lib", "src/phase1", "src/phase2", "src/audit"):
    sys.path.insert(0, str(ROOT / p))
