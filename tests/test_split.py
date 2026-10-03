import json

import pytest

from pagesight.data.split import load_split, save_split, split_queries

IDS = {"a": [f"a-q{i}" for i in range(10)], "b": [f"b-q{i}" for i in range(20)]}


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
