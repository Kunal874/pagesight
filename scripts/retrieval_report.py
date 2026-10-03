"""Task 5.5: results/retrieval_report.md from the single test run of each locked system (D-013,
D-031): ablation table, paired comparisons, index size per page, and example queries with page
thumbnails in results/figures/. Stops if a system has no test run, or more than one.

Usage: uv run python scripts/retrieval_report.py
"""

import json

from PIL import Image

from pagesight.config import SUBSETS
from pagesight.data.vidore import load_pages, load_queries
from pagesight.eval.compare import paired_difference
from pagesight.eval.runner import RESULTS, git_state
from pagesight.retrieval.bm25 import BM25Retriever
from pagesight.retrieval.colsmol import cache_path

SYSTEMS = {
    "bm25": "BM25 (text)",
    "dense_qwen3": "Dense Qwen3-Embedding-0.6B (text)",
    "colsmol_500m": "Visual brute force (GPU)",
    "qdrant_exact": "Visual exact (Qdrant) — main",
    "two_stage_mean": "Two-stage, mean-pooled first stage, N=25",
    "two_stage_binary": "Two-stage, binary first stage, N=25",
    "hybrid": "Hybrid: RRF of visual exact + BM25",
}
PAIRS = [
    ("qdrant_exact", "bm25"),
    ("qdrant_exact", "dense_qwen3"),
    ("hybrid", "qdrant_exact"),
    ("hybrid", "bm25"),
    ("hybrid", "dense_qwen3"),
    ("two_stage_binary", "qdrant_exact"),
    ("two_stage_mean", "qdrant_exact"),
    ("colsmol_500m", "qdrant_exact"),
]
METRICS = ["recall@1", "recall@5", "recall@10", "mrr@10"]
FIGURES = RESULTS / "figures"


def test_run(config: str) -> dict:
    runs = sorted(RESULTS.glob(f"{config}-test-*.json"))
    if len(runs) != 1:
        raise SystemExit(
            f"{config}: expected exactly one test run, found {len(runs)} (D-013)"
        )
    return json.loads(runs[0].read_text(encoding="utf-8"))


def dense_bytes_per_page() -> int:
    from pagesight.retrieval.dense import load_model

    vectors = load_model().encode_document(["a", "b"], convert_to_tensor=True)
    return vectors[0].nelement() * vectors[0].element_size()


def kb_per_page(subset: str, pages: list, dense: int) -> dict[str, str]:
    """On-disk (or in-memory, for BM25 and dense) index size per page."""
    n = len(pages)
    bm25 = sum(
        a.nbytes
        for a in BM25Retriever(pages).bm25.scores.values()
        if hasattr(a, "nbytes")
    )
    qdrant = json.loads((RESULTS / "qdrant_index.json").read_text(encoding="utf-8"))
    disk = qdrant["subsets"][subset]["disk_bytes"]
    cache = cache_path("vidore/colSmol-500M", subset).stat().st_size

    def kb(total_bytes: int) -> str:
        return f"{total_bytes / n / 1024:.1f}"

    return {
        "bm25": kb(bm25),
        "dense_qwen3": kb(dense * n),
        "colsmol_500m": kb(cache),
        "qdrant_exact": kb(disk["total"]),
        "two_stage_mean": kb(disk["total"]),
        "two_stage_binary": f"{kb(disk['total'])} (scan: {kb(disk['patches_binary'])})",
        "hybrid": kb(disk["total"] + bm25),
    }


def thumbnail(page) -> str:
    FIGURES.mkdir(exist_ok=True)
    path = FIGURES / f"{page.id}.jpg"
    with Image.open(page.image) as img:
        img = img.convert("RGB")
        img.thumbnail((320, 460))
        img.save(path, quality=80)
    return f"figures/{path.name}"


def top3(run: dict, subset: str, qid: str, gold: dict[str, int]) -> str:
    ranking = run["subsets"][subset]["per_query"][qid]["ranking"][:3]
    return ", ".join(f"{p} {'✓' if p in gold else '✗'}" for p in ranking)


def examples(runs: dict, lines: list[str]) -> None:
    """3 queries where both text systems miss the top 3 and visual exact is right at rank 1,
    then 1 where visual misses the top 10 and BM25 is right at rank 1. First match by query id,
    preferring one chart and one table query."""
    found = {"text failed, visual right": [], "visual failed, BM25 right": []}
    for subset in SUBSETS:
        pages = {p.id: p for p in load_pages(subset)}
        for q in sorted(load_queries(subset), key=lambda q: q.id):
            if q.id not in runs["bm25"]["subsets"][subset]["per_query"]:
                continue  # dev query
            m = {c: runs[c]["subsets"][subset]["per_query"][q.id] for c in runs}
            if (
                m["bm25"]["hit@3"] == m["dense_qwen3"]["hit@3"] == 0
                and m["qdrant_exact"]["hit@1"]
            ):
                found["text failed, visual right"].append((subset, q, pages))
            if m["qdrant_exact"]["hit@10"] == 0 and m["bm25"]["hit@1"]:
                found["visual failed, BM25 right"].append((subset, q, pages))
    wins, fails = found["text failed, visual right"], found["visual failed, BM25 right"]
    chosen = []
    for kind in ("Chart", "Table", None):  # None = any content type
        pick = next(
            (
                w
                for w in wins
                if w not in chosen and (kind is None or kind in w[1].content_types)
            ),
            None,
        )
        if pick:
            chosen.append(pick)
    picks = [("Text failed, visual right", w) for w in chosen]
    picks += [("Visual failed, BM25 right", w) for w in fails[:1]]
    lines += ["", "## Examples (test split)", ""]
    lines.append(
        f"Candidates: {len(wins)} queries where text failed and visual was right at rank 1; "
        f"{len(fails)} where visual missed the top 10 and BM25 was right at rank 1. "
        "✓ = a gold page."
    )
    for title, (subset, q, pages) in picks:
        visual = runs["qdrant_exact"]["subsets"][subset]["per_query"][q.id]["ranking"][
            0
        ]
        bm25 = runs["bm25"]["subsets"][subset]["per_query"][q.id]["ranking"][0]
        lines += [
            "",
            f"### {title}: `{q.id}` ({', '.join(q.content_types)})",
            "",
            f"> {q.text}",
            "",
            f"- Gold pages: {', '.join(f'{p} (grade {g})' for p, g in q.gold.items())}",
            f"- BM25 top 3: {top3(runs['bm25'], subset, q.id, q.gold)}",
            f"- Dense top 3: {top3(runs['dense_qwen3'], subset, q.id, q.gold)}",
            f"- Visual exact top 3: {top3(runs['qdrant_exact'], subset, q.id, q.gold)}",
            "",
            "| visual top 1 | BM25 top 1 |",
            "|---|---|",
            f"| ![{visual}]({thumbnail(pages[visual])}) | ![{bm25}]({thumbnail(pages[bm25])}) |",
        ]


def main() -> None:
    runs = {c: test_run(c) for c in SYSTEMS}
    dense = dense_bytes_per_page()
    git = git_state()
    lines = [
        "# Retrieval report (test split)",
        "",
        (
            f"Generated by `scripts/retrieval_report.py` at {git['commit']}"
            f"{'+dirty' if git['dirty'] else ''} from one test run per system (D-013): "
            + ", ".join(
                f"`{r['run_id']}` ({r['git']['commit']})" for r in runs.values()
            )
            + "."
        ),
        "Settings were locked on dev before the test runs (D-028–D-031). Latency is per query,",
        "including query embedding. KB/page = index size: BM25 score matrix, dense vectors, the",
        "bf16 ColSmol cache on disk, or the Qdrant collection on disk (allocated bytes, Group 4);",
        "for binary, also the 1-bit copy that the first stage scans.",
    ]
    for subset in SUBSETS:
        sizes = kb_per_page(subset, load_pages(subset), dense)
        s0 = runs["bm25"]["subsets"][subset]
        lines += [
            "",
            f"## {subset}: {s0['n_queries']} queries, {s0['n_pages']} pages",
            "",
            (
                "| system | nDCG@10 (95% CI) | R@1 | R@5 | R@10 | MRR@10 | p50 ms | p95 ms "
                "| KB/page | peak VRAM GB |"
            ),
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for config, label in SYSTEMS.items():
            s = runs[config]["subsets"][subset]
            m = s["metrics"]
            low, high = m["ndcg@10"]["ci95"]
            cells = [
                label,
                f"{m['ndcg@10']['mean']:.3f} ({low:.3f}–{high:.3f})",
                *(f"{m[k]['mean']:.3f}" for k in METRICS),
                f"{s['latency_ms']['p50']:.1f}",
                f"{s['latency_ms']['p95']:.1f}",
                sizes[config],
                f"{s['peak_vram_gb']}",
            ]
            lines.append(f"| {' | '.join(cells)} |")
        lines += [
            "",
            "| paired comparison (nDCG@10) | Δ mean (95% CI) | wins / ties / losses |",
            "|---|---|---|",
        ]
        for a, b in PAIRS:
            per_query = [
                {
                    q: v["ndcg@10"]
                    for q, v in runs[c]["subsets"][subset]["per_query"].items()
                }
                for c in (a, b)
            ]
            d = paired_difference(*per_query)
            low, high = d["ci95"]
            lines.append(
                f"| {SYSTEMS[a]} − {SYSTEMS[b]} | {d['mean_diff']:+.3f} ({low:+.3f} to {high:+.3f}) "
                f"| {d['wins']} / {d['ties']} / {d['losses']} |"
            )
    examples(runs, lines)
    lines += [
        "",
        "Page images: ViDoRe V3 (hr source documents CC BY 4.0; finance_en SEC filings, public",
        "domain); queries and relevance labels CC BY 4.0 (docs/DATA.md).",
    ]
    (RESULTS / "retrieval_report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print("saved results/retrieval_report.md")


if __name__ == "__main__":
    main()
