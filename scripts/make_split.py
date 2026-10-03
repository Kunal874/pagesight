"""Write configs/split.json: 30% dev / 70% test of the English queries, per subset (D-013)."""

from pagesight.config import SEED, SUBSETS
from pagesight.data.split import load_split, save_split, split_queries
from pagesight.data.vidore import load_queries

DEV_FRACTION = 0.3

ids = {subset: [q.id for q in load_queries(subset)] for subset in SUBSETS}
save_split(split_queries(ids, DEV_FRACTION, SEED), seed=SEED, dev_fraction=DEV_FRACTION)
split = load_split()  # re-read: also checks that dev and test do not overlap
for subset in SUBSETS:
    dev = sum(q.startswith(f"{subset}-") for q in split["dev"])
    test = sum(q.startswith(f"{subset}-") for q in split["test"])
    print(f"{subset}: dev {dev}, test {test}")
print(f"total: dev {len(split['dev'])}, test {len(split['test'])}")
