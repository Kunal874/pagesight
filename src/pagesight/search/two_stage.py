"""Visual search in Qdrant. A first stage picks max(N, k) candidate pages, exact float MaxSim reranks
them (D-027, D-030):
- "none": no first stage, exact float MaxSim on every page — the main visual system (D-031)
- "binary": MaxSim on the 1-bit copy of every patch vector, then Qdrant rescoring with the float
  originals (rescore=False keeps the binary scores: the compressed-only variant, D-025)
- "mean": one mean-pooled vector per page
"""

import torch
from qdrant_client import QdrantClient, models

from pagesight.data.vidore import Page, page_id
from pagesight.index.qdrant_store import connect, point_id
from pagesight.retrieval.colsmol import embed_query, load_model

# exact MaxSim on the float originals: skip the binary copy
EXACT = models.SearchParams(quantization=models.QuantizationSearchParams(ignore=True))


def two_stage(
    client: QdrantClient,
    subset: str,
    query: torch.Tensor,
    k: int,
    first_stage: str,
    n: int = 0,
    rescore: bool = True,
    query_filter: models.Filter | None = None,
) -> list[int]:
    """Point ids of the top k pages for a (tokens, 128) query."""
    vectors = query.tolist()
    if first_stage == "none":
        hits = client.query_points(
            subset,
            vectors,
            using="patches",
            limit=k,
            query_filter=query_filter,
            search_params=EXACT,
        ).points
    elif first_stage == "binary":
        quantization = models.QuantizationSearchParams(
            rescore=rescore, oversampling=max(n, k) / k
        )
        hits = client.query_points(
            subset,
            vectors,
            using="patches",
            limit=k,
            query_filter=query_filter,
            search_params=models.SearchParams(quantization=quantization),
        ).points
    elif first_stage == "mean":
        # pooled . mean query ranks pages like MaxSim against the pooled vector would
        prefetch = models.Prefetch(
            query=query.mean(dim=0).tolist(),
            using="pooled",
            limit=max(n, k),
            filter=query_filter,
        )
        hits = client.query_points(
            subset,
            vectors,
            using="patches",
            prefetch=prefetch,
            limit=k,
            query_filter=query_filter,
            search_params=EXACT,
        ).points
    else:
        raise ValueError(f"unknown first stage {first_stage!r}")
    return [h.id for h in hits]


class TwoStageRetriever:
    """Runner adapter: ColSmol embeds the query on the GPU, Qdrant runs both stages (D-024)."""

    def __init__(
        self,
        pages: list[Page],
        model: str,
        first_stage: str,
        n_candidates: int = 0,
        rescore: bool = True,
    ):
        self.subset = pages[0].id.rsplit("-", 1)[0]
        self.client = connect()
        self.model, self.processor = load_model(model)
        self.options = {
            "first_stage": first_stage,
            "n": n_candidates,
            "rescore": rescore,
        }
        ids = [point_id(p) for p in pages]
        # slice runs search only their own pages; dev and test search the whole collection
        if len(ids) < self.client.count(self.subset).count:
            has_id = models.HasIdCondition(has_id=ids)
            self.options["query_filter"] = models.Filter(must=[has_id])
        vectors = self.client.get_collection(self.subset).config.params.vectors
        # the collection state behind this run (the binary query encoding is a collection setting)
        self.stats = {"quantization": str(vectors["patches"].quantization_config)}

    def search(self, query: str, k: int) -> list[str]:
        q = embed_query(self.model, self.processor, query).float().cpu()
        ids = two_stage(self.client, self.subset, q, k, **self.options)
        return [page_id(self.subset, i) for i in ids]
