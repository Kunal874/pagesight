from pagesight.search.hybrid import rrf


def test_rrf_sums_reciprocal_ranks_across_systems():
    # k=60: b = 1/62 + 1/61, a = 1/61, d = 1/62, c = 1/63
    assert rrf([["a", "b", "c"], ["b", "d"]], k=60) == ["b", "a", "d", "c"]


def test_rrf_counts_ranks_from_one():
    # k=1: q = 1/3 + 1/3 beats p = r = 1/2; counting from 0 would tie all three at 1.0
    assert rrf([["p", "q"], ["r", "q"]], k=1) == ["q", "p", "r"]


def test_rrf_k_sets_how_much_agreement_beats_one_top_rank():
    # q is 4th in both lists, p 1st in one: k=60 gives q 2/64 > p 1/61; k=1 gives p 1/2 > q 2/5
    lists = [["p", "a", "b", "q"], ["c", "d", "e", "q"]]
    assert rrf(lists, k=60)[0] == "q"
    assert rrf(lists, k=1)[0] == "p"


def test_rrf_breaks_ties_by_first_appearance():
    assert rrf([["x", "y"], ["y", "x"]], k=60) == ["x", "y"]
