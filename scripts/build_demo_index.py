"""Task 9.2 (D-049, D-050, D-052): build the demo index — all 1,110 hr pages, searchable in process by
brute-force MaxSim (no Qdrant server). Copies data/hr (pages.jsonl, queries.jsonl, page images) and
the cached ColSmol-500M page vectors (bfloat16) into data/demo/hr/, with a dataset card for the
Hugging Face dataset repo. Checks that every page has its vectors.

Usage: uv run python scripts/build_demo_index.py -> data/demo/ (+ results/demo_index.json)
"""

import json
import shutil

import torch

from pagesight.config import DATA_DIR
from pagesight.data.vidore import load_pages, load_queries
from pagesight.eval.runner import RESULTS, git_state
from pagesight.retrieval.colsmol import cache_path

SUBSET, MODEL = "hr", "vidore/colSmol-500M"  # D-050, D-023
OUT = DATA_DIR / "demo"
CARD = """---
license: cc-by-4.0
language:
- en
pretty_name: PageSight demo index (ViDoRe V3 hr)
tags:
- visual-document-retrieval
- colpali
- rag
---

# PageSight demo index

All {pages} pages of the `hr` subset of the ViDoRe V3 benchmark, prepared for the PageSight demo: the
app searches them by exact MaxSim over the page vectors below, in memory, without a vector database.

## Contents

- `hr/pages.jsonl` — page id, image path, the page text (the dataset's OCR markdown), source document id, page number
- `hr/queries.jsonl` — the {queries} English queries with their graded gold pages and reference answers
- `hr/pages/` — the page images as published in ViDoRe V3
- `hr/vectors.pt` — ColSmol-500M (`vidore/colSmol-500M`) page embeddings in bfloat16: one 128-dimensional vector per
  image patch, {vectors:,} vectors in all (a dict from page id to tensor; load with `torch.load(..., weights_only=True)`)

## Source and licence

Derived from [`vidore/vidore_v3_hr`](https://huggingface.co/datasets/vidore/vidore_v3_hr) (CC BY 4.0). Its 14 source
documents are EU reports published under CC BY 4.0. Changes: only English queries kept; page embeddings added.
This derived dataset is shared under the same licence, CC BY 4.0.
"""


def main() -> None:
    git = git_state()
    src, dst = DATA_DIR / SUBSET, OUT / SUBSET
    dst.mkdir(parents=True, exist_ok=True)
    for name in ("pages.jsonl", "queries.jsonl"):
        shutil.copy2(src / name, dst / name)
    shutil.copytree(src / "pages", dst / "pages", dirs_exist_ok=True)
    vectors = torch.load(cache_path(MODEL, SUBSET), weights_only=True)
    pages, queries = load_pages(SUBSET, OUT), load_queries(SUBSET, OUT)
    missing = [p.id for p in pages if p.id not in vectors or not p.image.is_file()]
    if missing:
        raise SystemExit(f"pages without vectors or images: {missing[:5]}")
    torch.save({p.id: vectors[p.id] for p in pages}, dst / "vectors.pt")
    n_vectors = sum(len(vectors[p.id]) for p in pages)
    card = CARD.format(pages=len(pages), queries=len(queries), vectors=n_vectors)
    (OUT / "README.md").write_text(card, encoding="utf-8")
    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    result = {
        "git": git,
        "subset": SUBSET,
        "pages": len(pages),
        "queries": len(queries),
        "vectors": n_vectors,
        "dtype": str(next(iter(vectors.values())).dtype),
        "size_mb": round(size / 2**20, 1),
    }
    print(result)
    path = RESULTS / "demo_index.json"
    path.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(f"saved results/{path.name}; index in data/demo/")


if __name__ == "__main__":
    main()
