from pathlib import Path

import torch

from pagesight.data.vidore import Page
from pagesight.retrieval.bm25 import BM25Retriever
from pagesight.retrieval.dense import DenseRetriever


def page(pid: str, text: str) -> Page:
    return Page(id=pid, image=Path(f"{pid}.png"), text=text, doc_id="d", page_number=0)


PAGES = [
    page("p0", "Net interest income rose to 92 billion dollars in 2024."),
    page("p1", "Employment rate of women in the European Union, by country."),
    page("p2", ""),  # empty OCR text, like 31 real pages
    page("p3", "Board of directors and corporate governance."),
]


def test_bm25_ranks_the_page_sharing_the_query_words_first():
    assert BM25Retriever(PAGES).search("net interest income in 2024", k=2)[0] == "p0"


def test_bm25_returns_k_distinct_page_ids():
    ranking = BM25Retriever(PAGES).search("employment of women", k=4)

    assert ranking[0] == "p1"
    assert sorted(ranking) == ["p0", "p1", "p2", "p3"]


def test_bm25_handles_a_query_of_only_stopwords():
    assert len(BM25Retriever(PAGES).search("the of and", k=3)) == 3


class FakeModel:
    """Stands in for the 1.2 GB embedding model: fixed, normalized 2-d vectors."""

    def __init__(self):
        vectors = [(1, 0), (0, 1), (0.6, 0.8), (0.8, 0.6)]
        self.docs = {p.text: v for p, v in zip(PAGES, vectors, strict=True)}
        self.queries = {"women at work": (0.1, 0.99)}

    def encode_document(self, texts, **_):
        return torch.tensor([self.docs[t] for t in texts], dtype=torch.float32)

    def encode_query(self, texts, **_):
        return torch.tensor([self.queries[t] for t in texts], dtype=torch.float32)


def test_dense_ranks_pages_by_similarity_to_the_query_embedding():
    # Query (0.1, 0.99): dot products p1 0.99, p2 0.85, p3 0.67, p0 0.10.
    ranking = DenseRetriever(PAGES, model=FakeModel()).search("women at work", k=3)

    assert ranking == ["p1", "p2", "p3"]
