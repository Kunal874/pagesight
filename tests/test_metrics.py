import math

import pytest

from pagesight.eval.metrics import (
    bootstrap_ci,
    cohen_kappa,
    hit_at_k,
    mrr_at_k,
    ndcg_at_k,
    query_metrics,
    recall_at_k,
)

GOLD = {"a": 2, "b": 1}  # page -> grade
RANKING = ["x", "a", "b", "y"]  # gold pages at ranks 2 and 3


def test_ndcg_uses_grades_as_gains_with_log2_discount():
    # DCG = 2/log2(3) + 1/log2(4); ideal DCG = 2/log2(2) + 1/log2(3)  -> about 0.6697
    expected = (2 / math.log2(3) + 1 / 2) / (2 + 1 / math.log2(3))
    assert ndcg_at_k(RANKING, GOLD, k=10) == pytest.approx(expected)


def test_ndcg_ideal_dcg_does_not_depend_on_gold_order():
    expected = (2 / math.log2(3) + 1 / 2) / (2 + 1 / math.log2(3))
    assert ndcg_at_k(RANKING, {"b": 1, "a": 2}, k=10) == pytest.approx(expected)


def test_ndcg_is_one_for_the_ideal_ranking():
    assert ndcg_at_k(["a", "b", "x"], GOLD, k=10) == pytest.approx(1.0)


def test_ndcg_ideal_dcg_is_cut_at_k_when_there_are_more_gold_pages():
    # Real queries have up to 30 gold pages; ranks 11-12 must not raise the ideal DCG.
    gold = {f"g{i}": 1 for i in range(12)}
    assert ndcg_at_k(list(gold), gold, k=10) == pytest.approx(1.0)


def test_ndcg_ignores_gold_pages_below_the_cutoff():
    ranking = [f"x{i}" for i in range(10)] + ["a", "b"]
    assert ndcg_at_k(ranking, GOLD, k=10) == 0.0


def test_recall_is_the_share_of_gold_pages_in_the_top_k():
    assert [recall_at_k(RANKING, GOLD, k) for k in (1, 2, 3)] == [0.0, 0.5, 1.0]


def test_hit_is_one_once_any_gold_page_is_in_the_top_k():
    assert [hit_at_k(RANKING, GOLD, k) for k in (1, 2)] == [0.0, 1.0]


def test_mrr_is_the_reciprocal_rank_of_the_first_gold_page():
    assert mrr_at_k(RANKING, GOLD, k=10) == 0.5
    assert mrr_at_k(RANKING, GOLD, k=1) == 0.0


def test_query_metrics_computes_each_metric_at_its_own_cutoff():
    m = query_metrics(RANKING, GOLD)

    assert (m["recall@1"], m["recall@5"], m["hit@1"], m["hit@3"], m["mrr@10"]) == (
        0.0,
        1.0,
        0.0,
        1.0,
        0.5,
    )
    assert m["ndcg@10"] == pytest.approx(ndcg_at_k(RANKING, GOLD, k=10))


def test_bootstrap_ci_of_constant_values_is_that_value():
    assert bootstrap_ci([0.7] * 20) == pytest.approx((0.7, 0.7))


def test_bootstrap_ci_matches_the_normal_95_percent_interval():
    # 100 values, half 0 and half 1: mean 0.5, standard error 0.05 -> 95% CI about 0.40..0.60
    # (a 90% interval would be about 0.42..0.58, a 99% one about 0.37..0.63).
    low, high = bootstrap_ci([0.0, 1.0] * 50)
    assert 0.385 <= low <= 0.415
    assert 0.585 <= high <= 0.615


def test_bootstrap_ci_is_reproducible_with_a_seed():
    values = [0.0, 0.3, 1.0, 0.5, 0.8] * 10
    assert bootstrap_ci(values, seed=1) == bootstrap_ci(values, seed=1)
    assert bootstrap_ci(values, seed=1) != bootstrap_ci(values, seed=2)


def test_cohen_kappa_by_hand():
    # agree on 7 of 10 (p_o = 0.7); both raters use c, p, i 4, 2, 4 times
    # (p_e = (16 + 4 + 16) / 100 = 0.36), so kappa = 0.34 / 0.64
    a = list("ccccppiiii")
    b = list("cccppiiiic")
    assert cohen_kappa(a, b) == pytest.approx(0.34 / 0.64)


def test_cohen_kappa_is_one_for_identical_single_label_grades():
    assert cohen_kappa(["c", "c"], ["c", "c"]) == 1.0
