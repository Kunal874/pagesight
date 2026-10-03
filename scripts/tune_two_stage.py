"""Task 5.3: tune the binary first stage on DEV ONLY (D-028), on the real Qdrant server.
"kept" = share of the exact MaxSim top-10 in the returned top-10; "same order" = identical top-10.
Rule (D-028): per binary query encoding, the smallest N with kept >= 0.99 in both subsets; the pair
with the lower mean p50 wins and is left applied to the collections. Also measured: exact float scan,
binary without rescoring (D-025) and the mean-pooled first stage (D-027 comparison row).
Latency is the Qdrant call only (query embedding is the same for every row).

Usage: uv run python scripts/tune_two_stage.py -> results/two_stage_tuning.md
"""

import statistics
import time

import torch
from qdrant_client import QdrantClient, models

from pagesight.config import SUBSETS
from pagesight.data.split import load_split
from pagesight.data.vidore import load_queries, page_id
from pagesight.eval.metrics import query_metrics
from pagesight.eval.runner import RESULTS, git_state
from pagesight.index.qdrant_store import connect, wait_until_green
from pagesight.retrieval.colsmol import embed_query, load_model
from pagesight.search.two_stage import EXACT, two_stage

MODEL = "vidore/colSmol-500M"  # D-023
NS = [25, 50, 100, 200]
K = 10
ENCODINGS = [
    models.BinaryQuantizationQueryEncoding.DEFAULT,
    models.BinaryQuantizationQueryEncoding.SCALAR8BITS,
]
KEPT_RULE = 0.99  # D-028


def set_encoding(client: QdrantClient, encoding) -> None:
    binary = models.BinaryQuantizationConfig(query_encoding=encoding)
    diff = models.VectorParamsDiff(
        quantization_config=models.BinaryQuantization(binary=binary)
    )
    for subset in SUBSETS:
        client.update_collection(subset, vectors_config={"patches": diff})
        wait_until_green(client, subset)


def exact_top(client: QdrantClient, subset: str, vec: torch.Tensor) -> list[int]:
    hits = client.query_points(
        subset, vec.tolist(), using="patches", limit=K, search_params=EXACT
    ).points
    return [h.id for h in hits]


def measure(client, subset, queries, exact, search) -> dict[str, float]:
    for _, vec in queries[:3]:
        search(vec)  # warm-up, not timed
    kept, same, ndcg, ms = [], [], [], []
    for (q, vec), want in zip(queries, exact, strict=True):
        start = time.perf_counter()
        got = search(vec)
        ms.append(1000 * (time.perf_counter() - start))
        kept.append(len(set(got) & set(want)) / K)
        same.append(got == want)
        ndcg.append(query_metrics([page_id(subset, i) for i in got], q.gold)["ndcg@10"])
    return {
        "kept": statistics.fmean(kept),
        "same order": statistics.fmean(same),
        "nDCG@10": statistics.fmean(ndcg),
        "p50 ms": statistics.median(ms),
    }


def main() -> None:
    dev = set(load_split()["dev"])
    model, processor = load_model(MODEL)
    queries = {
        s: [
            (q, embed_query(model, processor, q.text).float().cpu())
            for q in load_queries(s)
            if q.id in dev
        ]
        for s in SUBSETS
    }
    del model
    torch.cuda.empty_cache()

    client = connect()
    exact = {s: [exact_top(client, s, vec) for _, vec in queries[s]] for s in SUBSETS}
    rows: dict[str, dict[str, dict]] = {}  # config -> subset -> metrics

    def add(name: str, **options) -> None:
        rows[name] = {
            s: measure(
                client,
                s,
                queries[s],
                exact[s],
                lambda vec, s=s: two_stage(client, s, vec, K, **options),
            )
            for s in SUBSETS
        }
        print(
            name,
            {s: {k: round(v, 3) for k, v in m.items()} for s, m in rows[name].items()},
        )

    rows["exact float scan"] = {
        s: measure(
            client, s, queries[s], exact[s], lambda vec, s=s: exact_top(client, s, vec)
        )
        for s in SUBSETS
    }
    for n in NS:
        add(f"mean, N={n}", first_stage="mean", n=n)
    winners = []
    for encoding in ENCODINGS:
        set_encoding(client, encoding)
        add(
            f"binary {encoding.value}, no rescore",
            first_stage="binary",
            n=K,
            rescore=False,
        )
        for n in NS:
            add(f"binary {encoding.value}, N={n}", first_stage="binary", n=n)
        passing = [
            n
            for n in NS
            if all(
                rows[f"binary {encoding.value}, N={n}"][s]["kept"] >= KEPT_RULE
                for s in SUBSETS
            )
        ]
        if passing:
            name = f"binary {encoding.value}, N={passing[0]}"
            p50 = statistics.fmean(rows[name][s]["p50 ms"] for s in SUBSETS)
            winners.append((p50, encoding, passing[0]))
    if winners:
        _, encoding, n = min(winners, key=lambda w: w[0])
        set_encoding(client, encoding)  # leave the collections in the chosen state
        chosen = f"binary first stage, query encoding `{encoding.value}`, N = {n}"
    else:
        chosen = "no setting met the rule; the collections keep the last encoding tried"
    client.close()

    git = git_state()
    lines = [
        "# Two-stage tuning (dev only)",
        "",
        (
            f"Generated by `scripts/tune_two_stage.py` at {git['commit']}"
            f"{'+dirty' if git['dirty'] else ''}: {MODEL}, Qdrant server, dev queries only."
        ),
        '"kept" = share of the exact MaxSim top-10 in the returned top-10; "same order" = identical',
        "top-10 list; p50 = Qdrant call only. Rule (D-028): smallest N with kept >= 0.99 in both",
        "subsets, per query encoding; lower mean p50 wins.",
        "",
        f"**Chosen: {chosen}.**",
    ]
    for subset in SUBSETS:
        metrics = list(next(iter(rows.values()))[subset])
        lines += [
            "",
            f"## {subset}: {len(queries[subset])} queries",
            "",
            f"| config | {' | '.join(metrics)} |",
            f"|---|{'---:|' * len(metrics)}",
        ]
        for name, by_subset in rows.items():
            cells = [f"{by_subset[subset][m]:.3f}" for m in metrics[:-1]]
            cells.append(f"{by_subset[subset]['p50 ms']:.1f}")
            lines.append(f"| {name} | {' | '.join(cells)} |")
    path = RESULTS / "two_stage_tuning.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"chosen: {chosen}; saved results/two_stage_tuning.md")


if __name__ == "__main__":
    main()
