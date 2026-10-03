# DECISIONS

Append-only. A recorded decision changes only with Kunal's explicit OK — add a new entry that supersedes the old one; never edit history.

## D-001 · Project name · 2026-10-03 · Group 0
- **Question:** What is the project/repo called?
- **Options:** PageSight · ChartSeek · DocLens · VisRAG-Lite · own name
- **Choice:** PageSight
- **Why:** Names the core idea — find the right page by looking at it. ChartSeek undersells tables and text pages; DocLens is generic; VisRAG-Lite reads like a fork of the published VisRAG system.
- **Consequences:** Python package `pagesight` under `src/pagesight/`. Final repo name and description are reconfirmed in Group 10.

## D-002 · Runtime environment · 2026-10-03 · Group 0
- **Question:** Where do Python and PyTorch run?
- **Options:** native Windows + Docker Desktop · WSL2 Ubuntu
- **Choice:** Native Windows + Docker Desktop
- **Why:** Simplest setup, and data on D:\ is read at native speed (WSL2 reaches Windows drives through a slow file-sharing bridge). Docker Desktop 29.6.2 is already installed.
- **Consequences:** All commands target PowerShell / Git Bash. Docker is used only for Qdrant (Group 4) and packaging (Group 9).

## D-003 · Package manager · 2026-10-03 · Group 0
- **Question:** Which Python package manager?
- **Options:** uv · venv + pip · conda
- **Choice:** uv
- **Why:** Fast; `uv.lock` pins exact versions so the environment is reproducible; uv installs Python 3.11 itself (only 3.14 is installed system-wide).
- **Consequences:** uv is installed once (ask first). `pyproject.toml` and `uv.lock` are committed. uv's cache lives on D: so packages hard-link into `.venv` instead of being copied across drives.

## D-004 · Memory files in git · 2026-10-03 · Group 0
- **Question:** Which project-memory files are committed?
- **Options:** commit DECISIONS.md + docs/, rest local · commit all · keep all local
- **Choice:** Commit DECISIONS.md and docs/. Keep CLAUDE.md, AGENTS.md, PROGRESS.md and docs/INTERVIEW_NOTES.md local (gitignored).
- **Why:** The repo shows the design reasoning; working notes and interview prep stay private.
- **Consequences:** Local-only files have no backup. Same rule applied to the other local working files: visual-rag-build-prompt.md, .claude/, .remember/.

## D-005 · Licence · 2026-10-03 · Group 0
- **Question:** Licence for the project code?
- **Options:** MIT · Apache-2.0
- **Choice:** MIT
- **Why:** Short and standard for portfolio repos; Apache-2.0's patent and NOTICE terms add nothing here.
- **Consequences:** `LICENSE` is MIT, (c) 2026 Kunal Chandrakar. It covers only our code; datasets and models keep their own licences (recorded in docs/DATA.md and the README).

## D-006 · GitHub timing · 2026-10-03 · Group 0
- **Question:** When does the code go to GitHub?
- **Options:** push only at the end · private backup repo now
- **Choice:** Push only at the end (Group 10)
- **Why:** Nothing leaves the laptop until the clean-history checks pass.
- **Consequences:** No remote, no push, no repo creation before Group 10. No offsite backup until then.

## D-007 · Commit identity · 2026-10-03 · Group 0
- **Question:** Which git identity authors the commits?
- **Options:** Kunal Chandrakar + gmail · keep global "Kunal" · Kunal Chandrakar + GitHub noreply
- **Choice:** `Kunal Chandrakar <kunalchandrakar2005@gmail.com>`, set at repo level
- **Why:** Matches the required identity; the global git config (user.name "Kunal") stays untouched.
- **Consequences:** The email is visible in public history. It must be verified on GitHub so commits link to the profile (checked in Group 10).

## D-008 · Where large files live · 2026-10-03 · Group 0
- **Question:** Free disk space on D: — settled by measurement instead of asking.
- **Measured:** D: 66.0 GB free of 68.4 GB; C: 663.3 GB free of 884.5 GB.
- **Choice:** Keep the brief's default: large files on D:, `HF_HOME=D:\hf-cache`.
- **Why:** Rough peak estimate of 35–50 GB (environment ~5, models ~20–30 including Group 6 VLM candidates, datasets ~5–10, indexes ~3) fits in 66 GB. This is an estimate, not a measurement.
- **Consequences:** Delete rejected VLM candidates after Group 6. Moving anything to C: needs a new decision.

## D-009 · PyTorch build · 2026-10-03 · Group 0
- **Question:** Which PyTorch CUDA build?
- **Options:** torch 2.13.0 with cu130 · cu132 · cu126
- **Choice:** torch 2.13.0+cu130, from the PyTorch cu130 package index
- **Why:** colpali-engine 0.3.18 (needed in Group 3) requires torch<2.14, and 2.13.0 is the newest release below that with Windows + Python 3.11 builds. cu130 is a 1.8 GB download (cu126: 2.4 GB); the driver supports CUDA ≤ 13.3; cu132 is newest but add-on GPU libraries can lag behind.
- **Consequences:** torch is pinned to ==2.13.0 through a uv index source. When colpali-engine is added (Group 3), torchvision must come from the same cu130 index.

## D-010 · Build backend · 2026-10-03 · Group 0
- **Question:** Which build backend makes `pagesight` importable from tests and scripts?
- **Options:** uv_build · hatchling · none (pytest pythonpath + sys.path workarounds)
- **Choice:** uv_build
- **Why:** uv's own backend — zero config, same toolchain as D-003.
- **Consequences:** Build-time requirement only; `uv sync` installs pagesight in editable mode.
