"""Per-query retrieval metrics (D-020).

`ranking` lists page ids, best first; `gold` maps page id -> grade (2 fully, 1 critically
relevant). Any grade counts as relevant for recall, hit rate and MRR; nDCG uses the grade
itself as the gain with a log2(rank + 1) discount, like trec_eval.
"""

import math

import numpy as np

from pagesight.config import SEED


def ndcg_at_k(ranking: list[str], gold: dict[str, int], k: int) -> float:
    dcg = sum(gold.get(p, 0) / math.log2(r + 1) for r, p in enumerate(ranking[:k], 1))
    ideal = sorted(gold.values(), reverse=True)[:k]
    idcg = sum(grade / math.log2(r + 1) for r, grade in enumerate(ideal, 1))
    return dcg / idcg


def recall_at_k(ranking: list[str], gold: dict[str, int], k: int) -> float:
    return len(gold.keys() & set(ranking[:k])) / len(gold)


def hit_at_k(ranking: list[str], gold: dict[str, int], k: int) -> float:
    return float(any(p in gold for p in ranking[:k]))


def mrr_at_k(ranking: list[str], gold: dict[str, int], k: int) -> float:
    return next((1 / r for r, p in enumerate(ranking[:k], 1) if p in gold), 0.0)


def bootstrap_ci(
    values: list[float], n_resamples: int = 1000, seed: int = SEED, level: float = 0.95
) -> tuple[float, float]:
    """Percentile bootstrap interval for the mean of per-query values: the queries are
    resampled with replacement n_resamples times."""
    v = np.asarray(values, dtype=float)
    rows = np.random.default_rng(seed).integers(0, len(v), size=(n_resamples, len(v)))
    low, high = np.quantile(v[rows].mean(axis=1), [(1 - level) / 2, (1 + level) / 2])
    return float(low), float(high)


def query_metrics(ranking: list[str], gold: dict[str, int]) -> dict[str, float]:
    return {
        "ndcg@10": ndcg_at_k(ranking, gold, 10),
        **{f"recall@{k}": recall_at_k(ranking, gold, k) for k in (1, 5, 10)},
        **{f"hit@{k}": hit_at_k(ranking, gold, k) for k in (1, 3, 5, 10)},
        "mrr@10": mrr_at_k(ranking, gold, 10),
    }


def cohen_kappa(a: list[str], b: list[str]) -> float:
    """Agreement of two graders beyond chance: (p_o - p_e) / (1 - p_e), where p_o is the observed
    agreement and p_e the agreement expected if both graded at random with their own label rates."""
    n = len(a)
    p_o = sum(x == y for x, y in zip(a, b, strict=True)) / n
    p_e = sum((a.count(label) / n) * (b.count(label) / n) for label in set(a) | set(b))
    return 1.0 if p_e == 1 else (p_o - p_e) / (1 - p_e)
