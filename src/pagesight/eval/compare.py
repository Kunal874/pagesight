"""Paired comparison of two runs on the same queries (used for the Group 3 go/no-go gate)."""

import statistics

from pagesight.eval.metrics import bootstrap_ci


def paired_difference(a: dict[str, float], b: dict[str, float]) -> dict:
    """a, b: query id -> metric value. Mean of the per-query differences a - b, its bootstrap
    95% interval, and how many queries a wins, ties and loses."""
    if a.keys() != b.keys():
        raise ValueError("the runs cover different queries")
    diffs = [a[q] - b[q] for q in sorted(a)]
    return {
        "mean_diff": statistics.fmean(diffs),
        "ci95": bootstrap_ci(diffs),
        "wins": sum(d > 0 for d in diffs),
        "ties": sum(d == 0 for d in diffs),
        "losses": sum(d < 0 for d in diffs),
    }
