import pymupdf
import pytest

from pagesight.data.pdf import render_pdf


@pytest.fixture
def pdf_path(tmp_path):
    doc = pymupdf.open()
    for text in ("Net income 42", "Page two"):
        page = doc.new_page(width=612, height=792)  # US letter, in points (1/72 inch)
        page.insert_text((72, 72), text)
    path = tmp_path / "report.pdf"
    doc.save(path)
    return path


def test_render_pdf_renders_each_page_at_the_given_dpi(pdf_path, tmp_path):
    pages = render_pdf(pdf_path, tmp_path / "out", dpi=200)

    # 612 x 792 pt at 200 dpi = 1700 x 2200 px, the size of finance_en's page images.
    sizes = [
        (pymupdf.Pixmap(str(p.image)).width, pymupdf.Pixmap(str(p.image)).height)
        for p in pages
    ]
    assert sizes == [(1700, 2200), (1700, 2200)]


def test_render_pdf_extracts_text_per_page_in_order(pdf_path, tmp_path):
    pages = render_pdf(pdf_path, tmp_path / "out", dpi=72)

    assert [(p.id, p.page_number, p.text.strip()) for p in pages] == [
        ("report-0", 0, "Net income 42"),
        ("report-1", 1, "Page two"),
    ]
