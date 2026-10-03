"""Project paths and the ViDoRe V3 subsets in use (DECISIONS.md D-012)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
SUBSETS = {"hr": "vidore/vidore_v3_hr", "finance_en": "vidore/vidore_v3_finance_en"}
