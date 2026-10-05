import pymupdf

from pagesight.data.vidore import load_pages, load_queries
from pagesight.security.inject import PAGES, build_pdf, injected, write_dataset


def render(path, dpi=200) -> bytes:
    with pymupdf.open(path) as doc:
        return doc[0].get_pixmap(dpi=dpi).samples


def first(attack: str, hidden: bool):
    return next(p for p in PAGES if p.attack == attack and p.hidden == hidden)


def test_white_on_white_injection_leaves_the_page_image_unchanged(tmp_path):
    page = first("hijack", hidden=True)
    build_pdf(tmp_path / "a.pdf", [page])
    build_pdf(tmp_path / "b.pdf", [page], inject=False)

    assert render(tmp_path / "a.pdf") == render(tmp_path / "b.pdf")


def test_visible_injection_changes_the_page_image(tmp_path):
    # control: the comparison above can tell an injected page from a clean one
    page = first("hijack", hidden=False)
    build_pdf(tmp_path / "a.pdf", [page])
    build_pdf(tmp_path / "b.pdf", [page], inject=False)

    assert render(tmp_path / "a.pdf") != render(tmp_path / "b.pdf")


def test_hidden_injection_is_in_the_pdf_text_layer(tmp_path):
    page = first("system", hidden=True)
    build_pdf(tmp_path / "a.pdf", [page])

    with pymupdf.open(tmp_path / "a.pdf") as doc:
        words = " ".join(doc[0].get_text().split())  # the textbox wraps lines
    assert page.marker in words


def test_each_query_answer_is_printed_on_its_gold_page(tmp_path):
    write_dataset(tmp_path / "security")

    pages = {p.id: p for p in load_pages("security", tmp_path)}
    queries = load_queries("security", tmp_path)
    assert len(pages) == 6 and len(queries) == 18
    for q in queries:
        (gold,) = q.gold
        assert q.answer in pages[gold].text


def test_injected_finds_the_page_marker_in_any_case():
    page = first("hijack", hidden=False)

    assert injected(page, page.marker.lower(), gold=["security-9"])
    assert not injected(page, "Sales were 537 [p:security-0].", gold=["security-0"])


def test_citing_the_cite_target_counts_only_when_it_is_not_the_answer_page():
    page = first("cite", hidden=False)
    output = f"Sales were 537 [p:{page.marker}]."

    assert injected(page, output, gold=["security-9"])
    assert not injected(page, output, gold=[page.marker])
