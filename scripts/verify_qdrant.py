"""Task 4.5: Qdrant's MaxSim ranking must equal our float32 brute force on the dev-slice queries,
each searching its subset's full index (D-015). Needs the GPU and a running Qdrant.

Usage: uv run python scripts/verify_qdrant.py -> results/qdrant_equality.json
"""

import json
import statistics
import time

import torch
from qdrant_client import models

from pagesight.config import SLICE_FILE, SUBSETS
from pagesight.data.vidore import load_pages, load_queries
from pagesight.eval.runner import RESULTS, git_state
from pagesight.index.qdrant_store import connect
from pagesight.retrieval.colsmol import ColSmolRetriever, embed_query
from pagesight.retrieval.maxsim import maxsim

MODEL = "vidore/colSmol-500M"  # D-023
K = 10
TOL = 1e-3  # float32 sums in a different order differ by ~1e-5 on scores of ~5-20
# exact MaxSim on the float32 originals: skip the binary copy (D-025)
EXACT = models.SearchParams(quantization=models.QuantizationSearchParams(ignore=True))


def main() -> None:
    client = connect()
    slices = json.loads(SLICE_FILE.read_text(encoding="utf-8"))
    result = {"model": MODEL, "k": K, "tolerance": TOL, "git": git_state()}
    for subset in SUBSETS:
        wanted = set(slices[subset]["queries"])
        queries = [q for q in load_queries(subset) if q.id in wanted]
        # brute force over the cached page vectors, float32 on the GPU (Group 3)
        brute = ColSmolRetriever(load_pages(subset), MODEL, batch_size=1)
        index_of = {pid: i for i, pid in enumerate(brute.ids)}
        identical, max_diff, latencies = 0, 0.0, []
        for q in queries:
            vec = embed_query(brute.model, brute.processor, q.text).float()
            scores = maxsim(vec, brute.pages, brute.mask)
            top = scores.topk(K)
            start = time.perf_counter()
            hits = client.query_points(
                subset, vec.tolist(), using="patches", limit=K, search_params=EXACT
            ).points
            latencies.append(time.perf_counter() - start)
            got = [index_of[f"{subset}-{h.id}"] for h in hits]
            identical += got == top.indices.tolist()
            # each hit's score vs the brute-force score of the same page, and rank by rank
            for rank, (h, i) in enumerate(zip(hits, got, strict=True)):
                diff = max(
                    abs(h.score - scores[i].item()),
                    abs(h.score - top.values[rank].item()),
                )
                max_diff = max(max_diff, diff)
        result[subset] = {
            "queries": len(queries),
            "identical_rankings": identical,
            "max_score_diff": max_diff,
            "passed": max_diff <= TOL,
            "qdrant_p50_ms": round(1000 * statistics.median(latencies), 1),
        }
        print(subset, result[subset])
        del brute
        torch.cuda.empty_cache()  # one model on the GPU at a time
    client.close()
    path = RESULTS / "qdrant_equality.json"
    path.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(f"saved {path.relative_to(RESULTS.parent).as_posix()}")


if __name__ == "__main__":
    main()
