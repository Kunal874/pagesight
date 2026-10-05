"""Task 9.2: how should the demo (D-050: all of hr, 1,110 pages) search without a Qdrant server? Compares,
on 20 hr dev queries, Qdrant local mode in memory (the app's code unchanged) with brute-force MaxSim in
PyTorch on the CPU and on the GPU: build time, query latency (query embedding excluded) and whether
the top-10 lists agree.

Usage: uv run python scripts/probe_demo_index.py -> results/demo_index_probe.json
"""

import json
import statistics
import time
import warnings

import torch
from qdrant_client import QdrantClient

from pagesight.data.split import load_split
from pagesight.data.vidore import load_pages, load_queries, page_id
from pagesight.eval.runner import RESULTS, git_state
from pagesight.index.qdrant_store import create_collection, index_pages
from pagesight.retrieval.colsmol import cache_path, embed_query, load_model
from pagesight.retrieval.maxsim import maxsim, pad
from pagesight.search.two_stage import EXACT

MODEL, SUBSET, QUERIES, K = "vidore/colSmol-500M", "hr", 20, 10


def timed(fn, queries) -> tuple[list[list[str]], float]:
    """Top-k ids per query and the median seconds per query."""
    tops, seconds = [], []
    for q in queries:
        start = time.perf_counter()
        tops.append(fn(q))
        seconds.append(time.perf_counter() - start)
    return tops, statistics.median(seconds)


def main() -> None:
    git = git_state()
    pages = load_pages(SUBSET)
    ids = [p.id for p in pages]
    cache = torch.load(cache_path(MODEL, SUBSET), weights_only=True)
    dev = set(load_split()["dev"])
    texts = [q.text for q in load_queries(SUBSET) if q.id in dev][:QUERIES]
    model, processor = load_model(MODEL)
    queries = [embed_query(model, processor, t).float().cpu() for t in texts]
    del model
    torch.cuda.empty_cache()
    rows = {}

    start = time.perf_counter()
    client = QdrantClient(":memory:")
    create_collection(client, SUBSET, binary=False)
    index_pages(client, SUBSET, pages, cache, batch_size=64)
    build = time.perf_counter() - start

    def qdrant(q):
        hits = client.query_points(
            SUBSET, q.tolist(), using="patches", limit=K, search_params=EXACT
        ).points
        return [page_id(SUBSET, h.id) for h in hits]

    with warnings.catch_warnings():  # local mode says it ignores search_params
        warnings.simplefilter("ignore")
        tops, p50 = timed(qdrant, queries)
    rows["qdrant local mode (CPU)"] = {"build_s": build, "p50_s": p50, "tops": tops}

    for device in ("cpu", "cuda"):
        start = time.perf_counter()
        padded, mask = pad([cache[i].to(device, torch.float32) for i in ids])
        build = time.perf_counter() - start

        def brute(q, padded=padded, mask=mask, device=device):
            scores = maxsim(q.to(device), padded, mask)
            return [ids[i] for i in scores.topk(K).indices.tolist()]

        tops, p50 = timed(brute, queries)
        rows[f"torch brute force ({device})"] = {
            "build_s": build,
            "p50_s": p50,
            "tops": tops,
            "gb": padded.numel() * 4 / 2**30,
        }
        del padded, mask
        torch.cuda.empty_cache()

    reference = rows["torch brute force (cuda)"]["tops"]
    result = {"git": git, "subset": SUBSET, "pages": len(ids), "queries": len(texts)}
    for name, row in rows.items():
        same = sum(t == r for t, r in zip(row.pop("tops"), reference, strict=True))
        result[name] = {k: round(v, 4) for k, v in row.items()} | {
            "top10_same_as_gpu": f"{same}/{len(texts)}"
        }
        print(name, result[name])
    path = RESULTS / "demo_index_probe.json"
    path.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(f"saved results/{path.name}")


if __name__ == "__main__":
    main()
