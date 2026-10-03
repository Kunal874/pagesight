"""Write configs/split.json (30% dev / 70% test per subset, D-013) and
configs/dev_slice.json (~100 pages per subset from dev queries, D-016)."""

import json

from pagesight.config import SEED, SLICE_FILE, SUBSETS
from pagesight.data.split import build_slice, load_split, save_split, split_queries
from pagesight.data.vidore import load_pages, load_queries

DEV_FRACTION = 0.3
SLICE_PAGES = 100  # per subset

queries = {subset: load_queries(subset) for subset in SUBSETS}
ids = {subset: [q.id for q in qs] for subset, qs in queries.items()}
save_split(split_queries(ids, DEV_FRACTION, SEED), seed=SEED, dev_fraction=DEV_FRACTION)
split = load_split()  # re-read: also checks that dev and test do not overlap
for subset in SUBSETS:
    dev = sum(q.startswith(f"{subset}-") for q in split["dev"])
    test = sum(q.startswith(f"{subset}-") for q in split["test"])
    print(f"{subset}: dev {dev}, test {test}")
print(f"total: dev {len(split['dev'])}, test {len(split['test'])}")

dev_ids = set(split["dev"])
slices = {"seed": SEED, "pages_per_subset": SLICE_PAGES}
for subset in SUBSETS:
    dev_queries = [q for q in queries[subset] if q.id in dev_ids]
    pages = [p.id for p in load_pages(subset)]
    slices[subset] = build_slice(dev_queries, pages, SLICE_PAGES, SEED)
    print(
        f"slice {subset}: {len(slices[subset]['queries'])} dev queries, "
        f"{len(slices[subset]['pages'])} pages"
    )
SLICE_FILE.write_text(json.dumps(slices, indent=1) + "\n", encoding="utf-8")
