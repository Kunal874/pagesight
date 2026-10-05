"""Hugging Face ZeroGPU Space entry for the PageSight demo (Task 9.3; D-048 to D-052): all 1,110 hr pages
searched in memory by exact MaxSim, Qwen3.5-4B answering on a 48 GB GPU. The four model calls run in
spaces.GPU workers, each with its own GPU-time budget.

Space variables: PAGESIGHT_INDEX_REPO (the demo index dataset repo, required). For a local smoke test:
PAGESIGHT_DEMO_DIR=<folder with hr/> skips the download, PAGESIGHT_VLM_4BIT=1 fits the 8 GB laptop.
"""

import os
import sys
from pathlib import Path

import spaces  # before torch is imported: ZeroGPU patches its CUDA

ROOT = Path(__file__).resolve().parent
# pagesight ships as source: its pyproject pins Python 3.11, the Space runs 3.12 (D-048)
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

from huggingface_hub import snapshot_download

from pagesight.answer.vlm import AnswerModel
from pagesight.security.upload import MAX_BYTES
from pagesight.service import PageSight
from pagesight.ui.app import build

# seconds of GPU per call; shorter budgets get better queue priority
DURATIONS = {"query": 20, "generate_answer": 90, "pages": 240, "heatmap": 30}


def gpu(f):
    return spaces.GPU(duration=DURATIONS[f.__name__])(f)


def main() -> None:
    local = os.environ.get("PAGESIGHT_DEMO_DIR")
    if local:
        data = Path(local)
    else:
        repo = os.environ["PAGESIGHT_INDEX_REPO"]  # set in the Space settings
        data = Path(snapshot_download(repo, repo_type="dataset"))
    vlm = AnswerModel(quantize=os.environ.get("PAGESIGHT_VLM_4BIT") == "1")
    vlm.load()  # on cuda at startup, as ZeroGPU requires
    uploads = ROOT / "uploads"
    svc = PageSight(
        vlm=vlm,
        subsets=["hr"],
        data_dir=data,
        upload_dir=uploads,
        index="memory",
        gpu=gpu,
    )
    build(svc).launch(allowed_paths=[str(data), str(uploads)], max_file_size=MAX_BYTES)


# guarded: the upload checks start a spawned process, which re-imports this file
if __name__ == "__main__":
    main()
