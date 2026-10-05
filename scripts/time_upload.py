"""Times the upload path on the heaviest upload the limits allow (Task 7.3, D-040): 50 real
finance_en page images in one image-only PDF — like a scanned report — chosen as the 50 pages with
the largest images whose PDF still fits in 20 MB; ingested 3 times. The parse timeout is set to
about 3x the slowest run.

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


def build(path: Path, images: list[Path]) -> None:
    doc = pymupdf.open()
    for image in images:
        page = doc.new_page(width=612, height=792)  # US letter, like the source pages
        page.insert_image(page.rect, filename=str(image))
    doc.save(
        path, deflate=True
    )  # without deflate the images are stored uncompressed (~28x)
    doc.close()


def heaviest_allowed(path: Path) -> None:
    """Pages sorted by image size; the 50-page window with the largest images whose PDF fits.
    The PDF re-encodes the images, so its size is checked after building and the budget shrinks
    by 5% until it fits."""
    images = sorted(
        (p.image for p in load_pages("finance_en")), key=lambda i: i.stat().st_size
    )
    sizes = [i.stat().st_size for i in images]
    budget = MAX_BYTES
    while True:
        start = max(
            i
            for i in range(len(sizes) - MAX_PAGES + 1)
            if sum(sizes[i : i + MAX_PAGES]) <= budget
        )
        build(path, images[start : start + MAX_PAGES])
        if path.stat().st_size <= MAX_BYTES:
            return
        budget = int(budget * 0.95)


def main() -> None:
    git = git_state()
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "heavy.pdf"
        heaviest_allowed(pdf)
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
