# Running PageSight

Two ways to run the app locally, plus the hosted demo. All need an NVIDIA GPU with 8 GB of memory (measured peak
6.34 GB with both models loaded, D-046).

## 1. Native (Windows or Linux) — the path used to build and evaluate everything

Prerequisites: [uv](https://docs.astral.sh/uv/), an NVIDIA driver supporting CUDA 13.0, Docker (for Qdrant only).

```bash
uv sync                                      # Python 3.11 + pinned packages (torch 2.13.0 with CUDA 13.0)
docker compose up -d                         # Qdrant v1.19.1 on 127.0.0.1:6333/6334
uv run python scripts/prepare_data.py        # ViDoRe V3 hr + finance_en into data/ (~1.7 GB download)
uv run python -m pagesight.eval.runner configs/colsmol_500m.yaml --split dev  # embeds all pages (~40 min)
uv run python -m pagesight.index.qdrant_store  # loads those cached page vectors into Qdrant
uv run python -m pagesight.ui.app            # UI + API at http://127.0.0.1:7860
```

Set `HF_HOME` to where model weights should live (they total ~10 GB). The first app start downloads ColSmol-500M and
Qwen3.5-4B; later starts can run with `HF_HUB_OFFLINE=1`.

## 2. Docker, with the GPU (Windows: Docker Desktop, WSL2 backend)

Prerequisites: Docker Desktop with the WSL2 backend and GPU support (NVIDIA driver on Windows; no CUDA toolkit
needed in WSL), `data/` prepared and the model weights already in `HF_HOME` (the container runs offline).

```bash
docker compose --profile app up -d --build   # builds the app image, starts Qdrant + the app
```

Then open http://127.0.0.1:7860. The image holds only code (`.dockerignore`); `data/` and `HF_HOME` are mounted.
Both ports are published on 127.0.0.1 only: Qdrant has no authentication, and the app is not hardened for the internet.

## 3. Hosted demo (Hugging Face ZeroGPU Space)

`space/app.py` runs the same UI on all 1,110 hr pages, searched in memory by exact MaxSim (no Qdrant, D-052), with
the answer model in bfloat16 on a 48 GB GPU. `scripts/build_demo_index.py` builds the index dataset;
`scripts/deploy_space.py` assembles the Space (and publishes it only with `--push`, which needs a write token in
`HF_TOKEN`). Local smoke test of the Space entry on an 8 GB GPU:

```bash
PAGESIGHT_DEMO_DIR=data/demo PAGESIGHT_VLM_4BIT=1 uv run python space/app.py
```
