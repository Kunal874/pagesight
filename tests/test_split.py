import json

import pytest

from pagesight.data.split import build_slice, load_split, save_split, split_queries
from pagesight.data.vidore import Query

IDS = {"a": [f"a-q{i}" for i in range(10)], "b": [f"b-q{i}" for i in range(20)]}

# 40 pages; query i has 3 gold pages of its own (s-3i .. s-3i+2), so no gold is shared.
PAGES = [f"s-{i}" for i in range(40)]
SLICE_QUERIES = [
    Query(
        id=f"s-q{i}",
        text="?",
        gold={f"s-{3 * i + k}": 1 for k in range(3)},
        answer="",
        generator="human",
        content_types=[],
    )
    for i in range(10)
]


def test_build_slice_keeps_every_gold_page_of_chosen_queries():
    # 20 pages -> gold budget 10 -> exactly 3 disjoint 3-page queries fit.
    sliced = build_slice(SLICE_QUERIES, PAGES, n_pages=20, seed=0)
    chosen = [q for q in SLICE_QUERIES if q.id in sliced["queries"]]

    assert len(chosen) == 3
    assert all(page in sliced["pages"] for q in chosen for page in q.gold)


def test_build_slice_fills_with_distinct_distractors_to_size():
    sliced = build_slice(SLICE_QUERIES, PAGES, n_pages=20, seed=0)

    assert len(sliced["pages"]) == len(set(sliced["pages"])) == 20


def test_build_slice_ignores_input_order():
    forward = build_slice(SLICE_QUERIES, PAGES, n_pages=20, seed=0)
    backward = build_slice(SLICE_QUERIES[::-1], PAGES[::-1], n_pages=20, seed=0)

    assert forward == backward


def test_split_queries_partitions_each_subset_30_70():
    split = split_queries(IDS, dev_fraction=0.3, seed=0)

    assert sorted(split["dev"] + split["test"]) == sorted(IDS["a"] + IDS["b"])
    assert sum(q.startswith("a-") for q in split["dev"]) == 3
    assert sum(q.startswith("b-") for q in split["dev"]) == 6


def test_split_queries_ignores_input_order():
    reversed_ids = {subset: ids[::-1] for subset, ids in IDS.items()}

    assert split_queries(reversed_ids, 0.3, seed=0) == split_queries(IDS, 0.3, seed=0)


def test_split_queries_uses_the_seed():
    assert (
        split_queries(IDS, 0.3, seed=0)["dev"] != split_queries(IDS, 0.3, seed=1)["dev"]
    )


def test_load_split_round_trips(tmp_path):
    path = tmp_path / "split.json"
    save_split(
        {"dev": ["a-q1"], "test": ["a-q2", "b-q0"]}, seed=7, dev_fraction=0.3, path=path
    )

    assert load_split(path) == {
        "seed": 7,
        "dev_fraction": 0.3,
        "dev": ["a-q1"],
        "test": ["a-q2", "b-q0"],
    }


def test_load_split_rejects_overlap(tmp_path):
    path = tmp_path / "split.json"
    path.write_text(
        json.dumps({"dev": ["a-q1"], "test": ["a-q1", "a-q2"]}), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="a-q1"):
        load_split(path)
