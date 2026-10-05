"""Group 8: can the app keep the query encoder (ColSmol-500M) and the answer model (Qwen3.5-4B NF4) on
the GPU together? Loads both, then answers the first 3 dev questions per subset exactly as the app will
(top 2 pages of the exact visual search, gate, answer), measuring peak VRAM and seconds per question.

Usage: uv run python scripts/probe_app_vram.py -> results/app_vram.json
"""

import json
import time

import torch

from pagesight.answer.vlm import AnswerModel, load_image
from pagesight.config import SUBSETS
from pagesight.data.split import load_split
from pagesight.data.vidore import load_pages, load_queries, page_id
from pagesight.eval.answers import PAGES_PER_ANSWER, respond
from pagesight.eval.runner import RESULTS, git_state
from pagesight.index.qdrant_store import connect
from pagesight.retrieval.colsmol import embed_query, load_model
from pagesight.search.two_stage import two_stage

PER_SUBSET = 3


def gib(n: int) -> float:
    return round(n / 2**30, 2)


def main() -> None:
    git = git_state()
    torch.cuda.reset_peak_memory_stats()
    model, processor = load_model("vidore/colSmol-500M")
    vlm = AnswerModel()
    vlm.load()
    loaded = {
        "allocated_gb": gib(torch.cuda.memory_allocated()),
        "free_gb": gib(torch.cuda.mem_get_info()[0]),
    }
    print("both loaded", loaded)
    client, dev, rows = connect(), set(load_split()["dev"]), []
    for subset in SUBSETS:
        pages = {p.id: p for p in load_pages(subset)}
        for q in [q for q in load_queries(subset) if q.id in dev][:PER_SUBSET]:
            start = time.perf_counter()
            vec = embed_query(model, processor, q.text).float().cpu()
            ids = two_stage(client, subset, vec, PAGES_PER_ANSWER, "none")
            shown = [page_id(subset, i) for i in ids]
            images = [load_image(pages[pid].image) for pid in shown]
            p_yes, output = respond(vlm, q.text, shown, images)
            torch.cuda.empty_cache()
            rows.append(
                {
                    "query": q.id,
                    "seconds": round(time.perf_counter() - start, 2),
                    "p_yes": round(p_yes, 3),
                    "output": output,
                }
            )
            print(rows[-1])
    result = {
        "git": git,
        "both_loaded": loaded,
        "peak_allocated_gb": gib(torch.cuda.max_memory_allocated()),
        "peak_reserved_gb": gib(torch.cuda.max_memory_reserved()),
        "total_gb": gib(torch.cuda.mem_get_info()[1]),
        "questions": rows,
    }
    path = RESULTS / "app_vram.json"
    path.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print({k: v for k, v in result.items() if k != "questions"})
    print(f"saved results/{path.name}")


if __name__ == "__main__":
    main()
