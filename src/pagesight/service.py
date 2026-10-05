"""The app's in-process service (D-043, D-046), shared by the API and the Gradio UI: both models stay
loaded, GPU work runs one request at a time behind a lock, and the CUDA cache is emptied after each
request. Sources are the benchmark subsets and uploaded PDFs (named by a hash of the file). Search runs
in Qdrant (the local app: one collection per source) or, for the demo, by brute-force MaxSim over page
vectors held in memory (D-052): no server, data_dir/<subset>/vectors.pt."""

import hashlib
import threading
import time
from dataclasses import dataclass, replace
from pathlib import Path

import torch
from PIL import Image
from qdrant_client import QdrantClient

from pagesight.answer.prompt import parse
from pagesight.answer.vlm import AnswerModel, load_image
from pagesight.config import DATA_DIR, SUBSETS
from pagesight.data.vidore import Page, load_pages, page_id
from pagesight.eval.answers import PAGES_PER_ANSWER, respond_retrying
from pagesight.index.qdrant_store import connect, create_collection, index_pages
from pagesight.retrieval.bm25 import BM25Retriever
from pagesight.retrieval.colsmol import (
    embed_pages,
    embed_query,
    heatmap,
    load_model,
    overlay,
)
from pagesight.retrieval.maxsim import maxsim, pad
from pagesight.search.two_stage import EXACT
from pagesight.security.upload import ingest

COLSMOL = "vidore/colSmol-500M"  # the main visual system (D-023, D-031)
TOP_K = 3  # thumbnails shown; the answer reads the top PAGES_PER_ANSWER of them
# Upload text is untrusted: a huge hidden text layer must not blow up the text prompt or BM25.
# 12,000 characters is above every benchmark page (max 10,042).
MAX_TEXT_CHARS = 12_000


@dataclass
class Hit:
    page_id: str
    score: float | None  # MaxSim score; None for BM25 pages
    image: Path


@dataclass
class Answer:
    mode: str  # "visual" or "text"
    status: str  # "answer", "not_found" or "invalid"
    text: str
    citations: list[str]
    shown: list[str]  # pages the model read
    hits: list[Hit]  # pages shown to the user, best first
    p_yes: float
    seconds: float


class Encoder:
    """ColSmol-500M on the GPU."""

    def __init__(self):
        self.model, self.processor = load_model(COLSMOL)

    def query(self, text: str) -> torch.Tensor:
        return embed_query(self.model, self.processor, text).float().cpu()

    @torch.inference_mode()
    def pages(self, pages: list[Page]) -> list[torch.Tensor]:
        return embed_pages(self.model, self.processor, pages, 1)  # batch 1 (D-022)

    def heatmap(self, image: Image.Image, question: str) -> Image.Image:
        return overlay(image, heatmap(self.model, self.processor, image, question))


class MemoryIndex:
    """Exact MaxSim over page vectors held in RAM, scored in float32 on the CPU (D-052)."""

    def __init__(self, vectors: dict[str, torch.Tensor]):
        self.ids = list(vectors)
        self.pages, self.mask = pad([vectors[i].float() for i in self.ids])

    def search(self, query: torch.Tensor, k: int) -> list[tuple[str, float]]:
        top = maxsim(query.float(), self.pages, self.mask).topk(min(k, len(self.ids)))
        return [
            (self.ids[i], s)
            for i, s in zip(top.indices.tolist(), top.values.tolist(), strict=True)
        ]


class PageSight:
    def __init__(
        self,
        client: QdrantClient | None = None,
        encoder=None,
        vlm=None,
        subsets=tuple(SUBSETS),
        upload_dir: Path = DATA_DIR / "uploads",
        data_dir: Path = DATA_DIR,
        index: str = "qdrant",
    ):
        if index not in ("qdrant", "memory"):
            raise ValueError(f"index must be 'qdrant' or 'memory', got {index!r}")
        self.client = None if index == "memory" else client or connect()
        self.encoder = encoder or Encoder()
        if vlm is None:
            vlm = AnswerModel()
            vlm.load()  # both models stay loaded (D-046)
        self.vlm = vlm
        self.upload_dir = upload_dir
        self.lock = threading.Lock()  # one GPU request at a time (D-046)
        self.data_dir = data_dir
        self.pages = {s: {p.id: p for p in load_pages(s, data_dir)} for s in subsets}
        self.memory = {}
        if index == "memory":
            self.memory = {
                s: MemoryIndex(
                    torch.load(data_dir / s / "vectors.pt", weights_only=True)
                )
                for s in subsets
            }
        self.bm25 = {
            s: BM25Retriever(list(ps.values())) for s, ps in self.pages.items()
        }
        self.names = {s: s for s in subsets}

    def sources(self) -> dict[str, str]:
        """Source id -> display name (an upload's file name is for display only)."""
        return dict(self.names)

    def source_pages(self, source: str) -> dict[str, Page]:
        if source not in self.pages:
            raise ValueError(f"unknown source: {source!r}")
        return self.pages[source]

    def search(self, question: str, source: str, k: int = TOP_K) -> list[Hit]:
        pages = self.source_pages(source)
        with self.lock:
            vec = self.encoder.query(question)
        if self.client is None:
            found = self.memory[source].search(vec, k)
        else:
            points = self.client.query_points(
                source, vec.tolist(), using="patches", limit=k, search_params=EXACT
            ).points
            found = [(page_id(source, p.id), p.score) for p in points]
        return [Hit(i, score, pages[i].image) for i, score in found]

    def ask(self, question: str, source: str) -> Answer:
        """Visual RAG: the top pages of the exact MaxSim search, read as images."""
        start = time.perf_counter()
        hits = self.search(question, source)
        read = hits[:PAGES_PER_ANSWER]
        images = [load_image(h.image) for h in read]
        return self.answer("visual", question, read, hits, images, start)

    def ask_text(self, question: str, source: str) -> Answer:
        """Text RAG for the Compare tab (D-045): BM25's top pages, read as text."""
        start = time.perf_counter()
        pages = self.source_pages(source)
        ids = self.bm25[source].search(question, min(PAGES_PER_ANSWER, len(pages)))
        hits = [Hit(i, None, pages[i].image) for i in ids]
        texts = [pages[i].text[:MAX_TEXT_CHARS] for i in ids]
        return self.answer("text", question, hits, hits, texts, start)

    def answer(self, mode, question, read, hits, pages, start) -> Answer:
        shown = [h.page_id for h in read]
        with self.lock:
            try:
                p_yes, output, _ = respond_retrying(self.vlm, question, shown, pages)
            finally:
                torch.cuda.empty_cache()  # the margin is small (D-046)
        parsed = parse(output, shown)
        return Answer(
            mode,
            parsed.status,
            parsed.text,
            parsed.citations,
            shown,
            hits,
            p_yes,
            round(time.perf_counter() - start, 2),
        )

    def heatmap(self, question: str, pid: str, source: str) -> Image.Image:
        """The page with the regions that best match the question in red (D-044, D-047)."""
        page = self.source_pages(source).get(pid)
        if page is None:
            raise ValueError(f"unknown page: {pid!r}")
        image = Image.open(page.image).convert("RGB")
        with self.lock:
            try:
                return self.encoder.heatmap(image, question)
            finally:
                torch.cuda.empty_cache()

    def index_pdf(self, data: bytes, name: str) -> str:
        """Checks (Group 7), renders, embeds and indexes an upload; returns its source id. The id is a
        hash of the bytes, so the same file is indexed once."""
        doc = "u" + hashlib.sha256(data).hexdigest()[:12]
        if doc in self.pages:
            return doc
        pages = ingest(data, doc, self.upload_dir / doc)  # raises UploadError
        pages = [replace(p, text=p.text[:MAX_TEXT_CHARS].strip()) for p in pages]
        with self.lock:
            try:
                vectors = self.encoder.pages(pages)
            finally:
                torch.cuda.empty_cache()
        vectors = dict(zip([p.id for p in pages], vectors, strict=True))
        if self.client is None:
            self.memory[doc] = MemoryIndex(vectors)
        else:
            create_collection(self.client, doc, binary=False)
            index_pages(self.client, doc, pages, vectors, batch_size=16)
        self.pages[doc] = {p.id: p for p in pages}
        self.bm25[doc] = BM25Retriever(pages)
        self.names[doc] = name
        return doc
