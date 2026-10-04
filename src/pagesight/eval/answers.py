"""Answer runs (Tasks 6.3, 6.5). Phase 1: the main visual system (D-031) retrieves the top 2 pages
per query (D-033); the split's abstention set (15 queries per subset, seed 42) is retrieved again
with all its gold pages removed, so NOT_FOUND is the only correct reply. Phase 2, after the
retriever is unloaded: the VLM answers (D-032, D-035) and the output is parsed strictly (6.2).
The retriever and the VLM are never on the GPU together (brief, Task 6.1).

Usage: uv run python -m pagesight.eval.answers --split dev [--limit N]   (test needs --final)
       -> results/answers-<split>-<UTC time>.json (not saved with --limit: pipeline checks)
"""

import argparse
import json
import time
from datetime import UTC, datetime

import numpy as np
import torch
from qdrant_client import models

from pagesight.answer.abstain import abstention_set
from pagesight.answer.prompt import build_messages, parse
from pagesight.answer.vlm import MAX_PIXELS, MODEL, REVISION, AnswerModel, load_image
from pagesight.config import SEED, SUBSETS
from pagesight.data.split import load_split
from pagesight.data.vidore import load_pages, load_queries, page_id
from pagesight.eval.runner import RESULTS, git_state
from pagesight.retrieval.colsmol import embed_query
from pagesight.search.two_stage import TwoStageRetriever, two_stage

PAGES_PER_ANSWER = 2  # D-033
ABSTAIN_PER_SUBSET = 15  # Task 6.3: about 30 queries per split


def share(part: int, whole: int) -> float | None:
    return part / whole if whole else None


def answer_metrics(records: list[dict]) -> dict:
    """Shares over answer records. A NOT_FOUND counts as justified when no gold page was shown
    (gold pages removed, or retrieval missed them)."""
    ans = [r for r in records if r["kind"] == "answerable"]
    abst = [r for r in records if r["kind"] == "abstain"]
    shown = [r for r in ans if r["gold_shown"]]
    answered = [r for r in ans if r["status"] == "answer"]
    refusals = [r for r in records if r["status"] == "not_found"]
    justified = [r for r in refusals if r["kind"] == "abstain" or not r["gold_shown"]]
    return {
        "answerable": len(ans),
        "abstain": len(abst),
        "answered": share(len(answered), len(ans)),
        "invalid": share(sum(r["status"] == "invalid" for r in ans), len(ans)),
        "wrong_not_found": share(
            sum(r["status"] == "not_found" for r in shown), len(shown)
        ),
        "citation_accuracy": share(
            sum(r["citations_gold"] for r in answered), len(answered)
        ),
        "abstention_recall": share(
            sum(r["status"] == "not_found" for r in abst), len(abst)
        ),
        "not_found_precision": share(len(justified), len(refusals)),
    }


def retrieve(split: set[str], abstain: set[str], limit: int | None) -> list[dict]:
    """Phase 1: the pages each query shows the VLM."""
    jobs = []
    for subset in SUBSETS:
        retriever = TwoStageRetriever(
            load_pages(subset), "vidore/colSmol-500M", first_stage="none"
        )
        queries = [q for q in load_queries(subset) if q.id in split][:limit]
        for q in queries:
            start = time.perf_counter()
            vec = (
                embed_query(retriever.model, retriever.processor, q.text).float().cpu()
            )
            embed_s = time.perf_counter() - start
            filters = {"answerable": None}
            if q.id in abstain:
                gold = [int(p.rsplit("-", 1)[1]) for p in q.gold]
                no_gold = models.Filter(must_not=[models.HasIdCondition(has_id=gold)])
                filters["abstain"] = no_gold
            for kind, query_filter in filters.items():
                start = time.perf_counter()
                ids = two_stage(
                    retriever.client,
                    subset,
                    vec,
                    PAGES_PER_ANSWER,
                    "none",
                    query_filter=query_filter,
                )
                jobs.append(
                    {
                        "query": q,
                        "subset": subset,
                        "kind": kind,
                        "shown": [page_id(subset, i) for i in ids],
                        "retrieve_s": embed_s + time.perf_counter() - start,
                    }
                )
        del retriever
        torch.cuda.empty_cache()  # one model on the GPU at a time
    return jobs


def answer(jobs: list[dict]) -> list[dict]:
    """Phase 2: the VLM reads the shown pages and answers."""
    pages = {p.id: p for s in SUBSETS for p in load_pages(s)}
    vlm = AnswerModel()
    records = []
    for n, job in enumerate(jobs, start=1):
        q, shown = job["query"], job["shown"]
        images = [load_image(pages[pid].image) for pid in shown]
        start = time.perf_counter()
        output = vlm.generate(build_messages(q.text, shown, images))
        answer_s = time.perf_counter() - start
        parsed = parse(output, shown)
        records.append(
            {
                "query": q.id,
                "subset": job["subset"],
                "kind": job["kind"],
                "generator": q.generator,
                "shown": shown,
                "gold_shown": any(pid in q.gold for pid in shown),
                "output": output,
                "status": parsed.status,
                "answer": parsed.text,
                "citations": parsed.citations,
                "citations_gold": all(c in q.gold for c in parsed.citations),
                "retrieve_s": round(job["retrieve_s"], 3),
                "answer_s": round(answer_s, 2),
            }
        )
        print(f"{n}/{len(jobs)} {q.id} {job['kind']} {parsed.status} {answer_s:.1f} s")
    vlm.unload()
    return records


def summary(records: list[dict]) -> dict:
    totals = [r["retrieve_s"] + r["answer_s"] for r in records]
    p50, p95 = np.percentile(totals, [50, 95])
    return {
        "all": answer_metrics(records),
        **{
            s: answer_metrics([r for r in records if r["subset"] == s]) for s in SUBSETS
        },
        "latency_s": {"p50": round(float(p50), 2), "p95": round(float(p95), 2)},
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument(
        "--final", action="store_true", help="confirm a one-off test run"
    )
    parser.add_argument("--limit", type=int, help="first N queries per subset only")
    args = parser.parse_args(argv)
    if args.split == "test" and not args.final:
        raise SystemExit(
            "The test split runs once per locked config (D-013); pass --final."
        )

    split = set(load_split()[args.split])
    abstain = set(abstention_set(sorted(split), ABSTAIN_PER_SUBSET, SEED))
    started = datetime.now(UTC)
    torch.cuda.reset_peak_memory_stats()
    records = answer(retrieve(split, abstain, args.limit))
    result = {
        "run_id": f"answers-{args.split}-{started:%Y%m%dT%H%M%SZ}",
        "split": args.split,
        "config": {
            "model": MODEL,
            "revision": REVISION,
            "pages_per_answer": PAGES_PER_ANSWER,
            "max_pixels": MAX_PIXELS,
            "abstain_per_subset": ABSTAIN_PER_SUBSET,
            "seed": SEED,
        },
        "git": git_state(),
        "started_utc": started.isoformat(timespec="seconds"),
        "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2),
        "summary": summary(records),
        "records": records,
    }
    print(json.dumps(result["summary"], indent=1))
    if args.limit is None:
        path = RESULTS / f"{result['run_id']}.json"
        path.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
        print(f"saved results/{path.name}")


if __name__ == "__main__":
    main()
