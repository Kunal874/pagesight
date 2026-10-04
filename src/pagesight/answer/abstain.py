"""Abstention set (Task 6.3): queries asked again with all their gold pages removed from retrieval,
so NOT_FOUND is the only correct reply (D-035). A fixed, seeded sample per subset and split."""

import random


def abstention_set(query_ids: list[str], per_subset: int, seed: int) -> list[str]:
    by_subset: dict[str, list[str]] = {}
    for qid in sorted(query_ids):  # sorted: the sample must not depend on input order
        by_subset.setdefault(qid.rsplit("-q", 1)[0], []).append(qid)
    rng = random.Random(seed)
    return sorted(q for ids in by_subset.values() for q in rng.sample(ids, per_subset))
