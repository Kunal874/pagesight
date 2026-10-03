"""Evaluation runner: a YAML config in -> results/<run_id>.json and rows in results/leaderboard.md.

Usage: uv run python -m pagesight.eval.runner configs/bm25.yaml --split dev
Each query searches only its own subset's pages (D-015). The test split needs --final (D-013).
"""

import argparse
import json
import statistics
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import torch
import yaml

from pagesight.config import ROOT, SLICE_FILE
from pagesight.data.split import load_split
from pagesight.data.vidore import Page, Query, load_pages, load_queries
from pagesight.eval.metrics import bootstrap_ci, query_metrics

RESULTS = ROOT / "results"
K = 10
COLUMNS = ["recall@1", "recall@5", "recall@10", "hit@1", "hit@3", "mrr@10"]


def retriever_class(name: str):
    if name == "bm25":
        from pagesight.retrieval.bm25 import BM25Retriever

        return BM25Retriever
    if name == "dense":
        from pagesight.retrieval.dense import DenseRetriever

        return DenseRetriever
    if name == "colsmol":
        from pagesight.retrieval.colsmol import ColSmolRetriever

        return ColSmolRetriever
    raise ValueError(f"unknown retriever {name!r}")


def select(
    split: str,
    subset: str,
    pages: list[Page],
    queries: list[Query],
    split_ids: dict,
    slices: dict,
) -> tuple[list[Page], list[Query]]:
    """dev/test search all pages of the subset (D-016); slice uses the smoke slice only."""
    if split == "slice":
        keep_pages, keep_queries = (
            set(slices[subset]["pages"]),
            set(slices[subset]["queries"]),
        )
        return [p for p in pages if p.id in keep_pages], [
            q for q in queries if q.id in keep_queries
        ]
    wanted = set(split_ids[split])
    return pages, [q for q in queries if q.id in wanted]


def summarize(per_query: list[dict[str, float]], latencies_s: list[float]) -> dict:
    metrics = {}
    for name in per_query[0]:
        values = [m[name] for m in per_query]
        metrics[name] = {"mean": statistics.fmean(values), "ci95": bootstrap_ci(values)}
    p50, p95 = np.percentile([1000 * t for t in latencies_s], [50, 95])
    return {
        "n_queries": len(per_query),
        "metrics": metrics,
        "latency_ms": {"p50": float(p50), "p95": float(p95)},
    }


def git_state() -> dict:
    def git(*args: str) -> str:
        # check=True: a failing git call must not be recorded as a clean tree
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()

    # dirty = code or config differs from the commit, including new untracked files
    code = ["src", "scripts", "configs", "pyproject.toml", "uv.lock"]
    return {
        "commit": git("rev-parse", "--short", "HEAD"),
        "dirty": bool(git("status", "--porcelain", "--", *code)),
    }


def evaluate_subset(
    retriever_cls, pages: list[Page], queries: list[Query], options: dict
) -> dict:
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    start = time.perf_counter()
    retriever = retriever_cls(pages, **options)
    index_seconds = time.perf_counter() - start
    per_query, latencies, rankings = [], [], {}
    for q in queries:
        start = time.perf_counter()
        rankings[q.id] = retriever.search(q.text, K)
        latencies.append(time.perf_counter() - start)
        per_query.append(query_metrics(rankings[q.id], q.gold))
    summary = summarize(per_query, latencies)
    summary["n_pages"] = len(pages)
    summary["index_seconds"] = round(index_seconds, 2)  # includes model loading
    summary.update(
        getattr(retriever, "stats", {})
    )  # e.g. ColSmol embedding time per page
    summary["peak_vram_gb"] = (
        round(torch.cuda.max_memory_allocated() / 2**30, 2)
        if torch.cuda.is_available()
        else None
    )
    summary["per_query"] = {
        q.id: {"ranking": rankings[q.id], **m}
        for q, m in zip(queries, per_query, strict=True)
    }
    del retriever
    if torch.cuda.is_available():
        torch.cuda.empty_cache()  # one model on the GPU at a time
    return summary


def append_leaderboard(result: dict) -> None:
    path = RESULTS / "leaderboard.md"
    if not path.exists():
        header = [
            "run",
            "split",
            "subset",
            "pages",
            "queries",
            "nDCG@10 (95% CI)",
            *COLUMNS,
            "p50 ms",
            "commit",
        ]
        path.write_text(
            "# Leaderboard\n\nOne row per run and subset; written by `pagesight.eval.runner`.\n\n"
            f"| {' | '.join(header)} |\n|{'---|' * len(header)}\n",
            encoding="utf-8",
        )
    rows = []
    for subset, s in result["subsets"].items():
        m = s["metrics"]
        low, high = m["ndcg@10"]["ci95"]
        cells = [
            result["run_id"],
            result["split"],
            subset,
            s["n_pages"],
            s["n_queries"],
            f"{m['ndcg@10']['mean']:.3f} ({low:.3f}–{high:.3f})",
            *(f"{m[c]['mean']:.3f}" for c in COLUMNS),
            f"{s['latency_ms']['p50']:.1f}",
            result["git"]["commit"] + ("+dirty" if result["git"]["dirty"] else ""),
        ]
        rows.append(f"| {' | '.join(map(str, cells))} |\n")
    with path.open("a", encoding="utf-8") as f:
        f.writelines(rows)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--split", choices=["slice", "dev", "test"], default="dev")
    parser.add_argument(
        "--final", action="store_true", help="confirm a one-off test-split run"
    )
    args = parser.parse_args(argv)
    if args.split == "test" and not args.final:
        raise SystemExit(
            "The test split runs once per locked config (D-013); pass --final."
        )

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    retriever_cls = retriever_class(config["retriever"])
    started = datetime.now(UTC)
    run_id = f"{args.config.stem}-{args.split}-{started:%Y%m%dT%H%M%SZ}"
    split_ids = load_split()
    slices = json.loads(SLICE_FILE.read_text(encoding="utf-8"))
    result = {
        "run_id": run_id,
        "config": config,
        "split": args.split,
        "git": git_state(),
        "started_utc": started.isoformat(timespec="seconds"),
        "subsets": {},
    }
    for subset in config["subsets"]:
        pages, queries = select(
            args.split,
            subset,
            load_pages(subset),
            load_queries(subset),
            split_ids,
            slices,
        )
        result["subsets"][subset] = evaluate_subset(
            retriever_cls, pages, queries, config.get("options", {})
        )
        s = result["subsets"][subset]
        print(
            f"{subset}: nDCG@10 {s['metrics']['ndcg@10']['mean']:.3f} "
            f"{tuple(round(x, 3) for x in s['metrics']['ndcg@10']['ci95'])} | "
            f"{s['n_queries']} queries, {s['n_pages']} pages | index {s['index_seconds']} s | "
            f"p50 {s['latency_ms']['p50']:.1f} ms | peak VRAM {s['peak_vram_gb']} GB"
        )
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"{run_id}.json").write_text(
        json.dumps(result, indent=1) + "\n", encoding="utf-8"
    )
    append_leaderboard(result)
    print(f"saved results/{run_id}.json")


if __name__ == "__main__":
    main()
