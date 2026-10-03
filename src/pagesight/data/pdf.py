"""User-PDF ingestion: render each page to PNG at the benchmark's DPI and extract its text."""

from pathlib import Path

import pymupdf

from pagesight.config import PDF_DPI
from pagesight.data.vidore import Page


def render_pdf(pdf_path: Path, out_dir: Path, dpi: int = PDF_DPI) -> list[Page]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pages = []
    with pymupdf.open(pdf_path) as doc:
        for i, page in enumerate(doc):
            image = out_dir / f"{i}.png"
            page.get_pixmap(dpi=dpi).save(str(image))
            pages.append(
                Page(
                    id=f"{pdf_path.stem}-{i}",
                    image=image,
                    text=page.get_text(),
                    doc_id=pdf_path.stem,
                    page_number=i,
                )
            )
    return pages
