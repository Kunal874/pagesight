"""Project paths and the ViDoRe V3 subsets in use (DECISIONS.md D-012)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
SUBSETS = {"hr": "vidore/vidore_v3_hr", "finance_en": "vidore/vidore_v3_finance_en"}
SPLIT_FILE = ROOT / "configs" / "split.json"  # committed, so the split is auditable
SLICE_FILE = ROOT / "configs" / "dev_slice.json"  # pipeline checks only (D-016)
SEED = 42
