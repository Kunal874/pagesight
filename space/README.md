---
title: PageSight
emoji: 📄
colorFrom: indigo
colorTo: red
sdk: gradio
sdk_version: 6.29.1
python_version: "3.12"
app_file: app.py
pinned: false
license: mit
short_description: Visual RAG for chart- and table-heavy PDFs, with citations
---

# PageSight — demo

Ask questions about PDFs full of tables and charts. PageSight finds the right page by looking at page **images**
(ColSmol-500M, MaxSim late interaction), and a small vision-language model (Qwen3.5-4B) answers with a page
citation, or says NOT_FOUND.

This demo searches all 1,110 pages of the ViDoRe V3 `hr` subset (CC BY 4.0), in memory. You can also upload a
PDF (up to 20 MB and 50 pages).

Note: the answer model runs in bfloat16 here; the reported evaluation used the same model in 4-bit on an 8 GB
laptop GPU, so answers can differ slightly.
