"""Dense text retrieval (D-019): Qwen3-Embedding-0.6B, cosine similarity of page and query embeddings."""

import torch

from pagesight.data.vidore import Page

MODEL = "Qwen/Qwen3-Embedding-0.6B"
REVISION = "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"  # pinned for reproducibility


def load_model():
    # heavy import, only when the real model is needed
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(
        MODEL, revision=REVISION, model_kwargs={"dtype": torch.bfloat16}
    )


class DenseRetriever:
    def __init__(self, pages: list[Page], model=None, batch_size: int = 4):
        self.ids = [p.id for p in pages]
        self.model = model or load_model()
        self.pages = self.model.encode_document(
            [p.text for p in pages],
            batch_size=batch_size,
            convert_to_tensor=True,
            normalize_embeddings=True,
        )

    def search(self, query: str, k: int) -> list[str]:
        # encode_query adds the model's retrieval instruction to the query
        q = self.model.encode_query(
            [query], convert_to_tensor=True, normalize_embeddings=True
        )
        scores = (q @ self.pages.T)[0]
        return [self.ids[i] for i in scores.topk(k).indices.tolist()]
