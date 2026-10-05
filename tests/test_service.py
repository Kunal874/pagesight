"""The app service on CPU, with fake models (tests/conftest.py)."""

import pytest

from pagesight.security.upload import UploadError

# Qdrant local mode always searches exactly and says so; the server honours EXACT
pytestmark = pytest.mark.filterwarnings("ignore:Local mode performs exact")


def test_an_uploaded_pdf_is_searchable_by_its_words(service, make_pdf):
    doc = service.index_pdf(make_pdf("alpha revenue", "beta costs"), "report.pdf")

    hits = service.search("beta", doc, k=2)

    assert [h.page_id for h in hits] == [f"{doc}-1", f"{doc}-0"]
    assert hits[0].score == pytest.approx(1.0, abs=1e-5)
    assert hits[0].image.is_file()
    assert service.sources()[doc] == "report.pdf"


def test_the_same_pdf_twice_is_indexed_once(service, make_pdf):
    data = make_pdf("alpha revenue")

    assert service.index_pdf(data, "a.pdf") == service.index_pdf(data, "b.pdf")
    assert service.encoder.pages_embedded == 1


def test_a_refused_upload_raises_the_upload_error(service):
    with pytest.raises(UploadError):
        service.index_pdf(b"not a pdf", "x.pdf")


def test_visual_ask_answers_from_the_top_pages_and_cites_one(service, make_pdf):
    doc = service.index_pdf(
        make_pdf("alpha revenue", "beta costs", "gamma staff"), "r.pdf"
    )

    answer = service.ask("gamma", doc)

    assert answer.mode == "visual" and answer.status == "answer"
    assert answer.text == "It is 42." and answer.citations == [f"{doc}-2"]
    assert answer.hits[0].page_id == f"{doc}-2"
    assert len(answer.shown) == 2 and len(answer.hits) == 3


def test_a_closed_gate_gives_not_found_with_the_closest_pages(service, make_pdf):
    service.vlm.yes = 0.1
    doc = service.index_pdf(make_pdf("alpha revenue", "beta costs"), "r.pdf")

    answer = service.ask("beta", doc)

    assert answer.status == "not_found" and answer.citations == []
    assert answer.hits[0].page_id == f"{doc}-1"


def test_text_ask_reads_the_bm25_pages_as_text(service, make_pdf):
    doc = service.index_pdf(make_pdf("alpha revenue", "beta costs"), "r.pdf")

    answer = service.ask_text("beta costs", doc)

    assert answer.mode == "text" and answer.shown[0] == f"{doc}-1"
    assert "beta costs" in service.vlm.seen[1]  # the page's text, right after its id


def test_upload_text_is_capped(service, monkeypatch, make_pdf):
    monkeypatch.setattr("pagesight.service.MAX_TEXT_CHARS", 10)
    doc = service.index_pdf(make_pdf("beta costs rose sharply", "alpha"), "r.pdf")

    assert service.pages[doc][f"{doc}-0"].text == "beta costs"


def test_unknown_sources_are_rejected(service):
    with pytest.raises(ValueError, match="unknown source"):
        service.search("beta", "nope", k=1)


def test_heatmap_is_drawn_on_the_requested_page(service, make_pdf):
    doc = service.index_pdf(make_pdf("alpha revenue", "beta costs"), "r.pdf")

    image = service.heatmap("beta", f"{doc}-1", doc)

    assert image.mode == "L" and image.size == (1700, 2200)  # letter page at 200 dpi


def test_heatmap_of_an_unknown_page_is_rejected(service, make_pdf):
    doc = service.index_pdf(make_pdf("alpha revenue"), "r.pdf")

    with pytest.raises(ValueError, match="unknown page"):
        service.heatmap("beta", f"{doc}-7", doc)
