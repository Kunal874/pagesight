# 90-second demo (Task 9.4)

Screen recording of the local app (`uv run python -m pagesight.ui.app`, then http://127.0.0.1:7860), 1280×720,
browser zoom 90%, cursor visible. Free recorders: Windows Game Bar (Win + Alt + R) or OBS Studio. Narration is
optional; the captions below can be added as on-screen text instead.

| time | on screen | say / caption |
|---|---|---|
| 0–8 s | Ask tab, empty | "Text-based RAG reads PDFs as extracted text, so chart values and table layouts get lost. PageSight searches the page *images* instead." |
| 8–30 s | Documents: **finance_en**. Click the example "citigroup 2024 performance comparison banking wealth", then **Ask**. Wait ~15 s. | "It finds the right page among 2,942 bank-report pages and answers with a citation: Banking $1,529 million, Wealth $1,002 million, page finance_en-1119." |
| 30–42 s | Tick **heatmap**, Ask again. Scroll to the cited page. | "The heatmap shows why: the Banking and Wealth rows and the 2024 columns match the question." |
| 42–60 s | **Compare** tab, same question and documents, **Compare**. | "Same question, same answer model. Text RAG (keyword search on extracted text) picks other pages and finds nothing; visual RAG answers." |
| 60–72 s | Ask tab, type a question the reports don't cover, e.g. "What was Apple's revenue in 2024?" (finance_en), **Ask**. | "When the pages don't contain the answer, it says NOT_FOUND and shows the closest pages instead of guessing." |
| 72–85 s | **Results** tab: Retrieval, then Answers. | "Measured once on 439 held-out questions: visual search beats keyword search on finance tables, nDCG@10 0.599 vs 0.516; 58% of answers usable; it runs on an 8 GB laptop GPU." |
| 85–90 s | Back to the Ask tab | "PageSight: visual RAG with citations and honest refusals. Code and report on GitHub." |

Before recording: run each step once (the first question after start-up is slower), and check that the Apple question
really returns NOT_FOUND — if it does not, pick another question the reports cannot answer.

After recording: share the video file; it is turned into a short README GIF (needs a converter such as ffmpeg,
which is not installed yet — ask first).
