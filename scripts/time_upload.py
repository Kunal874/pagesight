"""Times the upload path on a heavy upload that the limits still allow (Task 7.3, D-040): 50 real
finance_en page images (letter pages, evenly spaced over the corpus) in one image-only PDF — like a
scanned report — ingested 3 times. The parse timeout is set to about 3x the slowest run.

Usage: uv run python scripts/time_upload.py -> results/upload_timing.json
"""

import json
import tempfile
import time
from pathlib import Path

import pymupdf

from pagesight.data.vidore import load_pages
from pagesight.eval.runner import RESULTS, git_state
from pagesight.security.upload import MAX_BYTES, MAX_PAGES, ingest

REPEATS = 3


def build(path: Path) -> None:
    pages = load_pages("finance_en")
    doc = pymupdf.open()
    for p in pages[:: len(pages) // MAX_PAGES][:MAX_PAGES]:
        page = doc.new_page(width=612, height=792)  # US letter, like the source pages
        page.insert_image(page.rect, filename=str(p.image))
    doc.save(path)
    doc.close()


def main() -> None:
    git = git_state()
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "heavy.pdf"
        build(pdf)
        data = pdf.read_bytes()
        seconds = []
        for i in range(REPEATS):
            start = time.perf_counter()
            pages = ingest(data, f"heavy{i}", Path(tmp) / "out", timeout_s=600)
            seconds.append(round(time.perf_counter() - start, 2))
            print(f"run {i}: {len(pages)} pages in {seconds[-1]} s")
    result = {
        "git": git,
        "pages": len(pages),
        "pdf_mb": round(len(data) / 2**20, 2),
        "limit_mb": MAX_BYTES // 2**20,
        "seconds": seconds,
    }
    print(result)
    path = RESULTS / "upload_timing.json"
    path.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(f"saved results/{path.name}")


if __name__ == "__main__":
    main()
