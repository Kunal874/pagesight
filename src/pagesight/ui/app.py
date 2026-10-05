"""Gradio app (Task 8.2, D-043): Ask, Compare, Results and How-it-works tabs, mounted on the FastAPI
app so the UI and the API share one service and one set of models.

Usage: uv run python -m pagesight.ui.app  -> UI at http://127.0.0.1:7860, API at /health /search /ask
/index-pdf on the same port. Qdrant must be running (docker compose up -d).
"""

import os

from pagesight.config import DATA_DIR

# set before gradio is imported: no usage telemetry, and the copies of every page image and upload
# Gradio serves go to D: (data/, gitignored), not the system temp folder on C: (D-008)
os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
os.environ.setdefault("GRADIO_TEMP_DIR", str(DATA_DIR / "gradio_tmp"))

from pathlib import Path

import gradio as gr
import uvicorn

from pagesight.api.main import app as api
from pagesight.api.main import get_service
from pagesight.config import ROOT, SUBSETS
from pagesight.data.split import load_split
from pagesight.data.vidore import load_queries
from pagesight.security.upload import MAX_BYTES, MAX_PAGES, UploadError
from pagesight.service import Answer, PageSight

REPORTS = [
    ("Retrieval", "retrieval_report.md"),
    ("Answers", "answer_report.md"),
    ("Security", "security_report.md"),
]
HOW = """
```
Indexing (once): PDF page -> image -> ColSmol -> ~1,000 vectors, one per image patch -> Qdrant
Question:        question -> ColSmol -> one vector per word
Search:          MaxSim: for each word take its best-matching patch, add them up -> page score
Answer:          top 2 pages + question -> Qwen3.5-4B (4-bit)
                 YES/NO gate "do these pages answer it?" -> answer with [p:<page id>], or NOT_FOUND
```

1. Every page is searched as a **picture**, so chart values and table layouts are not lost in text extraction.
2. ColSmol cuts each page into small patches and turns each into a vector; the question becomes one vector per word.
3. A page's score adds, word by word, how well its best patch matches (MaxSim) — this finds small numbers in big tables.
4. A small vision-language model reads the top 2 page images and must cite the page it used.
5. Before answering it is asked "do these pages contain the answer?"; if not, it says NOT_FOUND and shows the closest pages.
6. Page text is treated as untrusted data; uploads are size-, page- and time-limited (see the Security report).
"""


def choices(svc: PageSight) -> list[tuple[str, str]]:
    return [(name, sid) for sid, name in svc.sources().items()]


def example_questions() -> list[list[str]]:
    """Two dev questions per subset (dev, never test: the test split stays an exam, D-013)."""
    dev = set(load_split()["dev"])
    return [
        [q.text, s]
        for s in SUBSETS
        for q in [q for q in load_queries(s) if q.id in dev][:2]
    ]


def answer_markdown(a: Answer) -> str:
    if a.status == "answer":
        head = f"{a.text}\n\n**Source:** {', '.join(a.citations)}"
    elif a.status == "not_found":
        head = "**NOT_FOUND**: the pages read do not contain the answer. The closest pages are shown."
    else:
        head = "The model's reply broke the required format (no valid citation), so it is not shown."
    read = "page images" if a.mode == "visual" else "page texts"
    return (
        f"{head}\n\n<sub>Read {len(a.shown)} {read} ({', '.join(a.shown)}) · "
        f"gate p(YES) {a.p_yes:.2f} · {a.seconds} s</sub>"
    )


def gallery(a: Answer) -> list[tuple[str, str]]:
    return [
        (str(h.image), h.page_id if h.score is None else f"{h.page_id} · {h.score:.2f}")
        for h in a.hits
    ]


def cited_page(a: Answer) -> tuple[str, str]:
    """The cited page, else the best hit: with NOT_FOUND the user still sees the closest page."""
    pid = a.citations[0] if a.citations else a.hits[0].page_id
    return pid, str(next(h.image for h in a.hits if h.page_id == pid))


def build(svc: PageSight) -> gr.Blocks:
    def ask(question: str, source: str, heat: bool):
        if not question.strip():
            raise gr.Error("Type a question first.")
        a = svc.ask(question.strip(), source)
        pid, image = cited_page(a)
        if heat:  # D-044, D-047: placement verified on synthetic pages
            image = svc.heatmap(question.strip(), pid, source)
        return answer_markdown(a), image, gallery(a)

    def upload(path: str | None):
        if path is None:
            return gr.Dropdown(), ""
        try:
            sid = svc.index_pdf(Path(path).read_bytes(), Path(path).name)
        except UploadError as e:
            raise gr.Error(str(e)) from None
        n = len(svc.source_pages(sid))
        return gr.Dropdown(choices=choices(svc), value=sid), f"Indexed {n} pages."

    def compare(question: str, source: str):
        if not question.strip():
            raise gr.Error("Type a question first.")
        visual, text = svc.ask(question, source), svc.ask_text(question, source)
        return (
            answer_markdown(visual),
            gallery(visual),
            answer_markdown(text),
            gallery(text),
        )

    # every hour, delete served copies older than a day
    with gr.Blocks(title="PageSight", delete_cache=(3600, 86400)) as demo:
        gr.Markdown(
            "# PageSight\nQuestions about PDFs full of tables and charts, answered from the "
            "**page images** with a page citation, or NOT_FOUND."
        )
        with gr.Tab("Ask"):
            with gr.Row():
                source = gr.Dropdown(choices(svc), value="hr", label="Documents")
                pdf = gr.File(
                    label=f"…or upload a PDF (≤ {MAX_BYTES // 2**20} MB, ≤ {MAX_PAGES} pages)",
                    file_types=[".pdf"],
                    type="filepath",
                )
            upload_status = gr.Markdown()
            question = gr.Textbox(
                label="Question",
                lines=2,
                placeholder="Type a question, or click an example below",
            )
            # right under the box: below the page images they were easy to miss
            gr.Examples(
                example_questions(),
                inputs=[question, source],
                label="Example questions (click one, then Ask)",
            )
            heat = gr.Checkbox(
                label="Show where the question matched on the cited page (heatmap, ~1 s more)"
            )
            ask_button = gr.Button("Ask", variant="primary")
            answer = gr.Markdown()
            with gr.Row():
                cited = gr.Image(label="Cited page", type="filepath", height=720)
                hits = gr.Gallery(
                    label="Top 3 pages (MaxSim score)", columns=1, height=720
                )
            pdf.upload(upload, inputs=pdf, outputs=[source, upload_status])
            ask_button.click(ask, [question, source, heat], [answer, cited, hits])
            question.submit(ask, [question, source, heat], [answer, cited, hits])
        with gr.Tab("Compare"):
            gr.Markdown(
                "Same question, same answer model: **visual RAG** (ColSmol search, the model reads "
                "page images) vs **text RAG** (BM25 search, the model reads page text). A live "
                "demo, not a measured result (D-045)."
            )
            with gr.Row():
                c_question = gr.Textbox(label="Question", scale=4)
                c_source = gr.Dropdown(
                    choices(svc), value="hr", label="Documents", scale=1
                )
            gr.Examples(
                example_questions(),
                inputs=[c_question, c_source],
                label="Example questions (click one, then Compare)",
            )
            c_button = gr.Button("Compare", variant="primary")
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### Visual RAG")
                    v_answer = gr.Markdown()
                    v_pages = gr.Gallery(columns=2, height=420)
                with gr.Column():
                    gr.Markdown("### Text RAG")
                    t_answer = gr.Markdown()
                    t_pages = gr.Gallery(columns=2, height=420)
            c_button.click(
                compare, [c_question, c_source], [v_answer, v_pages, t_answer, t_pages]
            )
        with gr.Tab("Results"):
            for name, file in REPORTS:
                with gr.Tab(name):
                    gr.Markdown((ROOT / "results" / file).read_text(encoding="utf-8"))
        with gr.Tab("How it works"):
            gr.Markdown(HOW)
    return demo


def main() -> None:
    svc = get_service()  # load both models before the first request
    app = gr.mount_gradio_app(
        api,
        build(svc),
        path="/",
        allowed_paths=[str(DATA_DIR)],  # page images; uploads live under data/uploads
        max_file_size=MAX_BYTES,
    )
    uvicorn.run(app, host="127.0.0.1", port=7860)  # this laptop only


if __name__ == "__main__":
    main()
