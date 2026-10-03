"""Hybrid search (D-029): the visual two-stage ranking and the BM25 ranking, merged with
Reciprocal Rank Fusion."""

from pagesight.data.vidore import Page
from pagesight.retrieval.bm25 import BM25Retriever
from pagesight.search.two_stage import TwoStageRetriever


def rrf(rankings: list[list[str]], k: int) -> list[str]:
    """Page score = sum over rankings of 1 / (k + rank), ranks counted from 1. Ties keep the order
    in which pages first appear (sorted() is stable, also with reverse=True)."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, page in enumerate(ranking, start=1):
            scores[page] = scores.get(page, 0.0) + 1 / (k + rank)
    return sorted(scores, key=scores.__getitem__, reverse=True)


class HybridRetriever:
    def __init__(self, pages: list[Page], visual: dict, depth: int, rrf_k: int):
        self.visual = TwoStageRetriever(pages, **visual)
        self.bm25 = BM25Retriever(pages)
        self.depth, self.rrf_k = depth, rrf_k
        self.stats = self.visual.stats

    def search(self, query: str, k: int) -> list[str]:
        rankings = [
            self.visual.search(query, self.depth),
            self.bm25.search(query, self.depth),
        ]
        return rrf(rankings, self.rrf_k)[:k]
