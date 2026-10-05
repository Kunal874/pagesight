"""The app service on CPU: real Qdrant (local mode), real upload checks, real BM25 and parsing; only the
two models are fakes. The fake encoder gives every word a fixed random unit vector, so MaxSim ranks a
page containing the query word first, as the real model should."""

import re
import zlib

import pymupdf
import pytest
import torch
from qdrant_client import QdrantClient

from pagesight.security.upload import UploadError
from pagesight.service import PageSight

# Qdrant local mode always searches exactly and says so; the server honours EXACT
pytestmark = pytest.mark.filterwarnings("ignore:Local mode performs exact")


def word_vector(word: str) -> torch.Tensor:
    g = torch.Generator().manual_seed(zlib.crc32(word.lower().encode()))
    v = torch.randn(128, generator=g)
    return v / v.norm()


class FakeEncoder:
    def __init__(self):
        self.pages_embedded = 0

    def query(self, text: str) -> torch.Tensor:
        return torch.stack([word_vector(w) for w in text.split()])

    def pages(self, pages) -> list[torch.Tensor]:
        self.pages_embedded += len(pages)
        return [torch.stack([word_vector(w) for w in p.text.split()]) for p in pages]


class FakeVLM:
    """Says YES with p_yes, then answers citing the first page it was shown."""

    def __init__(self, p_yes: float = 0.9):
        self.yes, self.seen = p_yes, []

    def p_yes(self, messages) -> float:
        return self.yes

    def generate(self, messages) -> str:
        texts = [c.get("text", "") for c in messages[1]["content"]]
        self.seen = texts
        first = re.search(r"\[p:([^\]]+)\]", texts[0]).group(1)
        return f"It is 42 [p:{first}]."


def pdf(*pages: str) -> bytes:
    doc = pymupdf.open()
    for text in pages:
        doc.new_page(width=612, height=792).insert_text((72, 72), text)
    return doc.tobytes()


@pytest.fixture
def service(tmp_path):
    return PageSight(
        client=QdrantClient(":memory:"),
        encoder=FakeEncoder(),
        vlm=FakeVLM(),
        subsets=[],
        upload_dir=tmp_path,
    )


def test_an_uploaded_pdf_is_searchable_by_its_words(service):
    doc = service.index_pdf(pdf("alpha revenue", "beta costs"), "report.pdf")

    hits = service.search("beta", doc, k=2)

    assert [h.page_id for h in hits] == [f"{doc}-1", f"{doc}-0"]
    assert hits[0].score == pytest.approx(1.0, abs=1e-5)
    assert hits[0].image.is_file()
    assert service.sources()[doc] == "report.pdf"


def test_the_same_pdf_twice_is_indexed_once(service):
    data = pdf("alpha revenue")

    assert service.index_pdf(data, "a.pdf") == service.index_pdf(data, "b.pdf")
    assert service.encoder.pages_embedded == 1


def test_a_refused_upload_raises_the_upload_error(service):
    with pytest.raises(UploadError):
        service.index_pdf(b"not a pdf", "x.pdf")


def test_visual_ask_answers_from_the_top_pages_and_cites_one(service):
    doc = service.index_pdf(pdf("alpha revenue", "beta costs", "gamma staff"), "r.pdf")

    answer = service.ask("gamma", doc)

    assert answer.mode == "visual" and answer.status == "answer"
    assert answer.text == "It is 42." and answer.citations == [f"{doc}-2"]
    assert answer.hits[0].page_id == f"{doc}-2"
    assert len(answer.shown) == 2 and len(answer.hits) == 3


def test_a_closed_gate_gives_not_found_with_the_closest_pages(service):
    service.vlm = FakeVLM(p_yes=0.1)
    doc = service.index_pdf(pdf("alpha revenue", "beta costs"), "r.pdf")

    answer = service.ask("beta", doc)

    assert answer.status == "not_found" and answer.citations == []
    assert answer.hits[0].page_id == f"{doc}-1"


def test_text_ask_reads_the_bm25_pages_as_text(service):
    doc = service.index_pdf(pdf("alpha revenue", "beta costs"), "r.pdf")

    answer = service.ask_text("beta costs", doc)

    assert answer.mode == "text" and answer.shown[0] == f"{doc}-1"
    assert "beta costs" in service.vlm.seen[1]  # the page's text, right after its id


def test_upload_text_is_capped(service, monkeypatch):
    monkeypatch.setattr("pagesight.service.MAX_TEXT_CHARS", 10)
    doc = service.index_pdf(pdf("beta costs rose sharply", "alpha"), "r.pdf")

    assert service.pages[doc][f"{doc}-0"].text == "beta costs"


def test_unknown_sources_are_rejected(service):
    with pytest.raises(ValueError, match="unknown source"):
        service.search("beta", "nope", k=1)
