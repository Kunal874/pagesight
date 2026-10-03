import json
from pathlib import Path

import pytest

from pagesight.data.vidore import (
    Page,
    Query,
    build_queries,
    load_pages,
    load_queries,
    write_jsonl,
)


def query_row(query_id: int, text: str, language: str) -> dict:
    # Every column of the ViDoRe V3 `queries` config (docs/DATA.md).
    return {
        "query_id": query_id,
        "query": text,
        "language": language,
        "query_types": ["numerical"],
        "query_format": "question",
        "content_type": ["Table"],
        "raw_answers": ["42"],
        "query_generator": "human",
        "query_generation_pipeline": None,
        "source_type": "image",
        "query_type_for_generation": "numerical",
        "answer": "42",
    }


def qrel_row(query_id: int, corpus_id: int, score: int) -> dict:
    return {
        "query_id": query_id,
        "corpus_id": corpus_id,
        "score": score,
        "content_type": ["Table"],
        "bounding_boxes": [{"annotator": 0, "x1": 10, "x2": 200, "y1": 30, "y2": 90}],
    }


# Query 1 is the French copy of query 0, as the benchmark stores translations as separate rows.
QUERIES = [
    query_row(0, "What was net income in 2024?", "english"),
    query_row(1, "Quel était le résultat net en 2024 ?", "french"),
]
QRELS = [qrel_row(0, 7, 2), qrel_row(0, 9, 1), qrel_row(1, 7, 2), qrel_row(1, 9, 1)]


def test_build_queries_drops_non_english_rows():
    assert [q.text for q in build_queries("hr", QUERIES, QRELS)] == [
        "What was net income in 2024?"
    ]


def test_build_queries_maps_graded_gold_to_subset_page_ids():
    assert build_queries("hr", QUERIES, QRELS) == [
        Query(
            id="hr-q0",
            text="What was net income in 2024?",
            gold={"hr-7": 2, "hr-9": 1},
            answer="42",
            generator="human",
            content_types=["Table"],
        )
    ]


def test_build_queries_rejects_english_query_without_gold():
    with pytest.raises(ValueError, match="hr-q0"):
        build_queries("hr", QUERIES, [qrel_row(1, 7, 2)])


def test_load_pages_resolves_images_under_subset_dir(tmp_path):
    (tmp_path / "hr").mkdir()
    page = Page(
        id="hr-7",
        image=Path("pages/7.png"),
        text="Net income",
        doc_id="report_2024",
        page_number=3,
    )
    write_jsonl(tmp_path / "hr" / "pages.jsonl", [page])

    assert load_pages("hr", tmp_path) == [
        Page(
            id="hr-7",
            image=tmp_path / "hr" / "pages" / "7.png",
            text="Net income",
            doc_id="report_2024",
            page_number=3,
        )
    ]
    # Forward slashes on disk, so data prepared on Windows also loads on Linux.
    stored = json.loads((tmp_path / "hr" / "pages.jsonl").read_text(encoding="utf-8"))
    assert stored["image"] == "pages/7.png"


def test_load_queries_round_trips(tmp_path):
    (tmp_path / "hr").mkdir()
    query = Query(
        id="hr-q0",
        text="Net income?",
        gold={"hr-7": 2, "hr-9": 1},
        answer="42",
        generator="sdg",
        content_types=["Chart"],
    )
    write_jsonl(tmp_path / "hr" / "queries.jsonl", [query])

    assert load_queries("hr", tmp_path) == [query]
