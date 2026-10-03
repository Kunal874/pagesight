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

## D-011 · Python install location · 2026-10-03 · Group 0
- **Question:** Where does uv install Python versions? (Raised by a failed install, not by the planned question list.)
- **Options:** uv default (`%APPDATA%\uv\python`) · `D:\uv-python`
- **Choice:** `D:\uv-python`, via `UV_PYTHON_INSTALL_DIR`
- **Why:** Commands here run from an MSIX-packaged desktop app, and Windows redirects such apps' AppData writes into private storage. uv's default install there failed (its folder link pointed at a path that did not exist) and would have been invisible to normal terminals. D: is not redirected and matches D-008.
- **Consequences:** `.venv` is based on `D:\uv-python\cpython-3.11…`, so it works from any terminal. Rule: tool state (Python installs, caches, models) stays off AppData. HF_HOME, UV_CACHE_DIR and UV_PYTHON_INSTALL_DIR are set as user environment variables and in the local tool settings.

## D-012 · ViDoRe V3 subsets · 2026-10-03 · Group 1
- **Question:** Which public, English-document ViDoRe V3 subsets do we use?
- **Options:** hr + finance_en · hr + computer_science · hr + pharmaceuticals · hr only (candidates and numbers in docs/DATA.md)
- **Choice:** `vidore/vidore_v3_hr` + `vidore/vidore_v3_finance_en`
- **Why:** hr is chart-heavy and finance_en (bank 10-K reports) is table-heavy, so together they test both halves of the claim that text extraction loses charts and tables. 4,052 pages and 627 English queries fit the laptop. Licences are clean: CC BY 4.0 annotations; source documents CC BY 4.0 (hr) and SEC public domain (finance_en). pharmaceuticals was dropped over an unverified licence on 825 book pages, industrial is the largest (5,244 pages), computer_science is the easiest and mostly text.
- **Consequences:** 1.71 GB parquet download (finance_en alone 1.27 GB, approved with this choice). Published ColSmol-256M nDCG@10 on English queries (hr 0.460, finance_en 0.477) is a ballpark sanity check for Group 3, not a like-for-like target (our test split is 70% of the queries).

## D-013 · Dev/test split · 2026-10-03 · Group 1
- **Question:** How are queries split into dev (tuning) and test (final numbers)?
- **Options:** 30/70 stratified · 50/50 · 20/80
- **Choice:** 30% dev / 70% test, stratified by subset, fixed seed
- **Why:** About 188 dev queries are enough to tune the candidate count and fusion settings; about 439 test queries keep confidence intervals tight.
- **Consequences:** Only English query rows are used, selected with `language == "english"` (the benchmark stores 6 language copies as separate rows). Human-written and synthetic queries are both kept, as in the benchmark; `query_generator` stays in the data for slicing results. Tuning uses dev only; test runs once per locked config.

## D-014 · Page text for text baselines · 2026-10-03 · Group 1
- **Question:** Which page text feeds the text baselines?
- **Options:** dataset-provided `markdown` · markdown + plain PyMuPDF text from the original PDFs · own OCR (not needed: text is provided)
- **Choice:** The dataset's `markdown` field
- **Why:** Zero extra work, and it is a strong baseline: the OCR text keeps tables as text rows, so a visual win has to be real.
- **Consequences:** The text baselines are OCR-text baselines, not naive PDF-text extraction; results and README must say so. Pages with empty markdown (hr: 12 of 1,110; finance_en: not yet counted) can only be found visually. PyMuPDF text extraction is still built for user-uploaded PDFs (Task 1.6).

## D-015 · Retrieval scope in evaluation · 2026-10-03 · Group 1
- **Question:** During evaluation, which pages does a query search?
- **Options:** its own subset only · both subsets combined
- **Choice:** Its own subset only — the ViDoRe protocol
- **Why:** Each subset is a separate retrieval task in the benchmark, so our numbers stay comparable to the published ones.
- **Consequences:** Retrieval and metrics run per subset. The demo index may still combine subsets.

## D-016 · Go/no-go test set and smoke slice · 2026-10-03 · Group 1
- **Question:** What does the Group 3 go/no-go test run on? Measured: dev queries have 5.3 gold pages on average, so the brief's ~200-page slice fits only 28 of the 188 dev queries.
- **Options:** full dev set + smoke slice · ~2,100-page slice (full hr + 1,035 finance pages) · ~200-page slice
- **Choice:** All 188 dev queries on each subset's full corpus (4,052 pages), plus a ~200-page smoke slice for quick pipeline checks
- **Why:** The benchmark setting makes the published ColSmol numbers a real sanity check, and every dev query counts in the gate. Slicing would save little: the dev queries' gold pages already cover 33% of hr's 1,110 pages.
- **Consequences:** Changes the brief's task 3.1 ("embed the dev-slice pages"): Group 3 embeds all 4,052 pages per tested model (time measured on a small batch first; ask if over 30 minutes), and Group 4 reuses those embeddings. The smoke slice (configs/dev_slice.json) is for pipeline checks only, never for reported numbers.

## D-017 · Render DPI for uploaded PDFs · 2026-10-03 · Group 1
- **Question:** At what DPI does PyMuPDF render user PDFs? Settled by a quick test, not asked.
- **Measured:** the smallest hr source PDF (`undeclared_care_work_in_the_eu-TJ0125004ENN.pdf`, 52 pages): page 0 renders at 827 × 1170 (100 dpi), 1241 × 1754 (150 dpi) and 1654 × 2339 (200 dpi); the dataset's image of that page is 1654 × 2339. Render + PNG encode: 61, 114 and 173 ms per page.
- **Options:** 100 · 150 · 200 dpi
- **Choice:** 200 dpi
- **Why:** It reproduces the benchmark's page images exactly, so uploaded pages look to the retriever like the pages it was evaluated on. 173 ms per page is about 9 s for a 50-page upload.
- **Consequences:** `PDF_DPI = 200` in config.py; letter pages render at 1700 × 2200, A4 pages at 1654 × 2339.

## D-018 · Plain-language explanations · 2026-10-03 · Group 1
- **Question:** Kunal asked for one very simple explanation file per completed group, in a separate folder. Is it committed?
- **Options:** local folder (gitignored) · committed folder
- **Choice:** Local folder `explanation of project/`, one file per completed group
- **Why:** Personal learning notes, like docs/INTERVIEW_NOTES.md (D-004). Defaulted without a question; Kunal can ask to commit them.
- **Consequences:** Written at the end of every group (rule in the session instructions); listed in .gitignore.

## D-019 · Text baselines · 2026-10-03 · Group 2
- **Question:** Which text baselines do we build? BM25 is always included; which dense (meaning-based) model joins it?
- **Options:** + Qwen3-Embedding-0.6B · + granite-embedding-small-english-r2 · + bge-small-en-v1.5 · BM25 only (sizes, licences and context lengths read from the Hugging Face API on 2026-10-03)
- **Choice:** BM25 (bm25s) + `Qwen/Qwen3-Embedding-0.6B`
- **Why:** Same size class as ColSmol (596M vs 256–500M parameters), so text vs visual is a fair comparison. It reads whole pages (32,768-token limit; median page text is 3,127–3,809 characters). Apache-2.0, no custom code.
- **Consequences:** 1.19 GB weight download, approved with this choice. Dependencies bm25s and sentence-transformers (approved list). Both baselines run over the dataset's OCR markdown (D-014), per subset (D-015).

## D-020 · Recall definition · 2026-10-03 · Group 2
- **Question:** How is Recall@k defined, given about 5 gold pages per query?
- **Options:** standard recall + hit rate · standard recall only · hit rate only
- **Choice:** Standard Recall@k (share of a query's gold pages in the top k) plus Hit@k (at least one gold page in the top k)
- **Why:** Standard recall stays comparable with benchmark tooling; Hit@k predicts the answer step, which reads only the top 1–3 pages.
- **Consequences:** Any grade (1 or 2) counts as relevant for recall, hit rate and MRR; nDCG@10 uses the grade itself as the gain (trec_eval convention). Reported: nDCG@10, Recall@1/5/10, Hit@1/3/5/10, MRR@10.

## D-021 · ColSmol models for the go/no-go test · 2026-10-03 · Group 3
- **Question:** Which ColSmol model(s) does the Group 3 go/no-go test use?
- **Options:** both 256M and 500M · only 500M · only 256M
- **Choice:** Both: `vidore/colSmol-256M` (LoRA adapter, 39 MB, on `vidore/ColSmolVLM-Instruct-256M-base`, 456 MB) and `vidore/colSmol-500M` (70 MB adapter on `vidore/ColSmolVLM-Instruct-500M-base`, 921 MB); all MIT, not gated (Hugging Face API, 2026-10-03)
- **Why:** 256M is the model behind the published numbers (sanity check); 500M is likely stronger, which matters because BM25 on our dev split (hr 0.484, finance_en 0.488) already exceeds the published 256M scores (0.460, 0.477).
- **Consequences:** 1.49 GB download, approved with this choice. Each model embeds all 4,052 pages (D-016): time a small batch first, ask before any run over 30 minutes. colpali-engine 0.3.18, with torchvision pinned to the cu130 index (D-009).

## D-022 · ColSmol batch size · 2026-10-03 · Group 3
- **Question:** Which batch size for embedding pages? Settled by measurement (results/colsmol_probe.md), not asked.
- **Measured:** 32 pages, batch 1 / 2 / 4 / 8 — 256M: 2.7 / 2.5 / 2.6 / 2.5 pages/s at 0.89 / 1.33 / 2.22 / 3.98 GB peak VRAM; 500M: 2.3 / 2.2 / 2.2 / 2.1 pages/s at 1.34 / 1.78 / 2.67 / 4.44 GB.
- **Choice:** batch size 1 for both models
- **Why:** Throughput does not grow with batch size, so the bottleneck is not the GPU (likely CPU-side image preprocessing; not profiled), while memory grows 4–5×. Batch 1 is as fast as any and leaves the most VRAM free.
- **Consequences:** Embedding all 4,052 pages takes about 26 min (256M) and 29 min (500M). Pages give 875 (hr, A4) or 1,139 (finance_en, letter) vectors each.

## D-023 · Go/no-go gate · 2026-10-04 · Group 3
- **Question:** Does visual retrieval pass the gate (beats BM25 on nDCG@10 AND fits in VRAM), and which model goes forward?
- **Evidence (results/go_no_go.md; dev split, 188 queries):** nDCG@10 — ColSmol-256M hr 0.507, finance_en 0.529; ColSmol-500M hr 0.528, finance_en 0.560; BM25 0.484 / 0.488; dense 0.448 / 0.552. 500M minus BM25 (paired 95% interval): hr +0.044 (−0.016 to +0.103), finance_en +0.072 (+0.010 to +0.131); 500M minus dense: hr +0.080 (+0.014 to +0.152), finance_en +0.008 (−0.066 to +0.072). Peak VRAM 4.10 of 6.9 GB.
- **Options:** GO with ColSmol-500M · GO with both models · NO-GO
- **Choice:** GO with ColSmol-500M
- **Why:** Both models meet the brief's rule; only 500M has clear wins (vs BM25 on finance_en, vs dense on hr), and it never scores below either text baseline.
- **Consequences:** Groups 4–5 use ColSmol-500M; its page vectors are already cached under indexes/colsmol/. ColSmol-256M results stay as the published-number sanity check. The trade-off is reported: about 190–250 ms per query vs 0.3 ms for BM25, and about 40 minutes to embed the corpus.
