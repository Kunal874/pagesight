"""ViDoRe V3: download each subset into data/<subset>/, then load pages and queries."""

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

from pagesight.config import DATA_DIR

_IMAGE_EXT = {b"\x89PNG": ".png", b"\xff\xd8\xff": ".jpg"}


@dataclass
class Page:
    id: str
    image: Path
    text: str  # OCR markdown shipped with the dataset (D-014); may be empty
    doc_id: str
    page_number: int  # 0-based page index in the source PDF


@dataclass
class Query:
    id: str
    text: str
    gold: dict[str, int]  # page id -> grade: 2 fully relevant, 1 critically relevant
    answer: str
    generator: str  # "human" or "sdg" (synthetic)
    content_types: list[str]


def page_id(subset: str, corpus_id: int) -> str:
    return f"{subset}-{corpus_id}"


def build_queries(
    subset: str, query_rows: Iterable[dict], qrel_rows: Iterable[dict]
) -> list[Query]:
    """English queries with graded gold pages; other-language copies are dropped."""
    gold: dict[int, dict[str, int]] = {}
    for row in qrel_rows:
        pages = gold.setdefault(row["query_id"], {})
        pages[page_id(subset, row["corpus_id"])] = row["score"]

    queries = []
    for row in query_rows:
        if row["language"] != "english":
            continue
        qid = f"{subset}-q{row['query_id']}"
        if not gold.get(row["query_id"]):
            raise ValueError(f"{qid} has no relevant pages")
        queries.append(
            Query(
                id=qid,
                text=row["query"],
                gold=gold[row["query_id"]],
                answer=row["answer"],
                generator=row["query_generator"],
                content_types=row["content_type"],
            )
        )
    return queries


def write_jsonl(path: Path, rows: Iterable) -> None:
    # as_posix: data prepared on Windows must also load on Linux (Docker, Space).
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            line = json.dumps(asdict(row), ensure_ascii=False, default=Path.as_posix)
            f.write(line + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def load_pages(subset: str, data_dir: Path = DATA_DIR) -> list[Page]:
    root = data_dir / subset
    rows = _read_jsonl(root / "pages.jsonl")
    return [Page(**{**row, "image": root / row["image"]}) for row in rows]


def load_queries(subset: str, data_dir: Path = DATA_DIR) -> list[Query]:
    return [Query(**row) for row in _read_jsonl(data_dir / subset / "queries.jsonl")]


def prepare_subset(subset: str, repo: str, data_dir: Path = DATA_DIR) -> None:
    """Download a subset: page images (original bytes), pages.jsonl, queries.jsonl."""
    from datasets import Image, load_dataset  # heavy import, only needed here

    root = data_dir / subset
    (root / "pages").mkdir(parents=True, exist_ok=True)
    corpus = load_dataset(repo, "corpus", split="test")
    pages = []
    for row in corpus.cast_column("image", Image(decode=False)):
        cid, data = row["corpus_id"], row["image"]["bytes"]
        ext = next((e for magic, e in _IMAGE_EXT.items() if data.startswith(magic)), "")
        if not ext:
            raise ValueError(f"{subset} corpus_id {cid}: unknown image format")
        image = Path("pages", f"{cid}{ext}")
        if not (root / image).exists():
            (root / image).write_bytes(data)
        pages.append(
            Page(
                id=page_id(subset, cid),
                image=image,
                text=row["markdown"] or "",
                doc_id=row["doc_id"],
                page_number=row["page_number_in_doc"],
            )
        )
    query_rows = load_dataset(repo, "queries", split="test")
    qrel_rows = load_dataset(repo, "qrels", split="test")
    write_jsonl(root / "pages.jsonl", pages)
    write_jsonl(root / "queries.jsonl", build_queries(subset, query_rows, qrel_rows))
