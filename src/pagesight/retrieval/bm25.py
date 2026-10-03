"""BM25 keyword search over page text (D-019): bm25s, English stopwords, no stemming."""

import bm25s

from pagesight.data.vidore import Page


class BM25Retriever:
    def __init__(self, pages: list[Page]):
        self.ids = [p.id for p in pages]
        tokens = bm25s.tokenize([p.text for p in pages], show_progress=False)
        self.bm25 = bm25s.BM25()
        self.bm25.index(tokens, show_progress=False)

    def search(self, query: str, k: int) -> list[str]:
        tokens = bm25s.tokenize([query], return_ids=False, show_progress=False)
        docs, _ = self.bm25.retrieve(tokens, k=k, show_progress=False)
        return [self.ids[i] for i in docs[0]]
