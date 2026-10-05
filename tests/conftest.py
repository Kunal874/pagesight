"""Fakes for the app's two models, shared by test_service.py and test_api.py: everything else (Qdrant
in local mode, upload checks, BM25, parsing) is real. The fake encoder gives every word a fixed random
unit vector, so MaxSim ranks a page containing the query word first, as the real model should."""

import re
import zlib

import pymupdf
import pytest
import torch
from qdrant_client import QdrantClient

from pagesight.service import PageSight


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
def make_pdf():
    return pdf


@pytest.fixture
def service(tmp_path):
    return PageSight(
        client=QdrantClient(":memory:"),
        encoder=FakeEncoder(),
        vlm=FakeVLM(),
        subsets=[],
        upload_dir=tmp_path,
    )
