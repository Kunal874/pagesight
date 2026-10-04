from pagesight.answer.abstain import abstention_set

IDS = [f"hr-q{i}" for i in range(40)] + [f"finance_en-q{i}" for i in range(30)]


def test_samples_the_same_number_from_each_subset():
    chosen = abstention_set(IDS, per_subset=5, seed=42)
    assert len(chosen) == 10
    assert sum(q.startswith("hr-") for q in chosen) == 5
    assert set(chosen) <= set(IDS)


def test_is_reproducible_and_independent_of_input_order():
    once = abstention_set(IDS, per_subset=5, seed=42)
    assert abstention_set(list(reversed(IDS)), per_subset=5, seed=42) == once
    assert abstention_set(IDS, per_subset=5, seed=7) != once
