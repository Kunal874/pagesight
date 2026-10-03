import pytest

from pagesight.eval.compare import paired_difference


def test_paired_difference_compares_the_same_queries():
    a = {"q1": 0.5, "q2": 1.0, "q3": 0.0}
    b = {"q1": 0.25, "q2": 1.0, "q3": 0.5}  # differences +0.25, 0, -0.5

    result = paired_difference(a, b)

    assert result["mean_diff"] == pytest.approx(-0.25 / 3)
    assert (result["wins"], result["ties"], result["losses"]) == (1, 1, 1)


def test_paired_difference_ci_of_a_constant_gap_is_that_gap():
    a = {f"q{i}": 0.6 for i in range(20)}
    b = {f"q{i}": 0.5 for i in range(20)}

    assert paired_difference(a, b)["ci95"] == pytest.approx((0.1, 0.1))


def test_paired_difference_rejects_runs_over_different_queries():
    with pytest.raises(ValueError, match="different queries"):
        paired_difference({"q1": 1.0}, {"q2": 1.0})
