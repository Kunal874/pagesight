from pathlib import Path

import pytest

from pagesight.data.vidore import Page, Query
from pagesight.eval.runner import main, select, summarize

PAGES = [
    Page(id=f"hr-{i}", image=Path(f"{i}.png"), text="", doc_id="d", page_number=i)
    for i in range(4)
]
QUERIES = [
    Query(
        id=f"hr-q{i}",
        text="?",
        gold={"hr-0": 1},
        answer="",
        generator="human",
        content_types=[],
    )
    for i in range(3)
]
SPLIT = {"dev": ["hr-q0", "finance_en-q5"], "test": ["hr-q1", "hr-q2"]}
SLICE = {"hr": {"queries": ["hr-q2"], "pages": ["hr-0", "hr-3"]}}


def test_select_dev_searches_all_pages_with_only_dev_queries():
    pages, queries = select("dev", "hr", PAGES, QUERIES, SPLIT, SLICE)

    assert len(pages) == 4
    assert [q.id for q in queries] == ["hr-q0"]


def test_select_slice_restricts_both_pages_and_queries():
    pages, queries = select("slice", "hr", PAGES, QUERIES, SPLIT, SLICE)

    assert [p.id for p in pages] == ["hr-0", "hr-3"]
    assert [q.id for q in queries] == ["hr-q2"]


def test_summarize_reports_means_and_latency_percentiles():
    summary = summarize(
        [{"ndcg@10": 1.0}, {"ndcg@10": 0.0}], latencies_s=[0.001, 0.003]
    )

    assert summary["metrics"]["ndcg@10"]["mean"] == 0.5
    # linear interpolation between 1 ms and 3 ms: p50 = 2 ms, p95 = 1 + 0.95 * 2 = 2.9 ms
    assert summary["latency_ms"] == pytest.approx({"p50": 2.0, "p95": 2.9})


def test_test_split_is_refused_without_the_final_flag():
    with pytest.raises(SystemExit, match="--final"):
        main(["configs/does-not-matter.yaml", "--split", "test"])
