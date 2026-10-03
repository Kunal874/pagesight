"""Dev/test split of query ids (D-013): tune on dev only; run test once per locked config."""

import json
import random
from pathlib import Path

from pagesight.config import SPLIT_FILE
from pagesight.data.vidore import Query


def split_queries(
    ids_by_subset: dict[str, list[str]], dev_fraction: float, seed: int
) -> dict[str, list[str]]:
    """Stratified: each subset is shuffled with the same seed and cut at dev_fraction."""
    split: dict[str, list[str]] = {"dev": [], "test": []}
    for ids in ids_by_subset.values():
        ids = sorted(ids)  # the input order must not change the split
        random.Random(seed).shuffle(ids)
        cut = round(len(ids) * dev_fraction)
        split["dev"] += ids[:cut]
        split["test"] += ids[cut:]
    return split


def save_split(
    split: dict[str, list[str]], seed: int, dev_fraction: float, path: Path = SPLIT_FILE
) -> None:
    record = {"seed": seed, "dev_fraction": dev_fraction, **split}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")


def load_split(path: Path = SPLIT_FILE) -> dict:
    split = json.loads(path.read_text(encoding="utf-8"))
    if overlap := set(split["dev"]) & set(split["test"]):
        raise ValueError(f"dev and test share query ids: {sorted(overlap)[:5]}")
    return split


def build_slice(
    queries: list[Query], page_ids: list[str], n_pages: int, seed: int
) -> dict[str, list[str]]:
    """Smoke slice of one subset (D-016): queries whose gold pages fit in half of
    n_pages, all of those gold pages, and random distractor pages up to n_pages."""
    rng = random.Random(seed)
    order = sorted(queries, key=lambda q: q.id)  # the input order must not matter
    rng.shuffle(order)
    chosen, gold = [], set()
    for q in order:
        if len(gold.union(q.gold)) <= n_pages // 2:
            chosen.append(q.id)
            gold.update(q.gold)
    distractors = rng.sample(sorted(set(page_ids) - gold), n_pages - len(gold))
    return {"queries": sorted(chosen), "pages": sorted(gold | set(distractors))}
