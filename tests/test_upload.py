import pymupdf
import pytest

from pagesight.security.upload import MAX_BYTES, MAX_PAGES, UploadError, check, ingest


def pdf_bytes(pages: int = 2, **save_options) -> bytes:
    doc = pymupdf.open()
    for i in range(pages):
        doc.new_page(width=612, height=792).insert_text((72, 72), f"Page {i}")
    return doc.tobytes(**save_options)


def opened(data: bytes) -> pymupdf.Document:
    return pymupdf.open(stream=data, filetype="pdf")


def test_a_valid_pdf_is_rendered_page_by_page(tmp_path):
    pages = ingest(pdf_bytes(2), "report", tmp_path)

    assert [p.id for p in pages] == ["report-0", "report-1"]
    assert all(p.image.is_file() for p in pages)
    assert pages[1].text.strip() == "Page 1"


def test_files_over_the_size_limit_are_rejected_before_parsing(tmp_path):
    data = b"%PDF-1.7\n" + b"0" * MAX_BYTES

    with pytest.raises(UploadError, match="20 MB"):
        ingest(data, "big", tmp_path)


def test_files_without_a_pdf_header_are_rejected(tmp_path):
    with pytest.raises(UploadError, match="not a PDF"):
        ingest(b"<html>hello</html>", "page", tmp_path)


def test_malformed_pdfs_are_rejected(tmp_path):
    truncated = pdf_bytes(2)[:300]

    with pytest.raises(UploadError, match="malformed"):
        ingest(truncated, "broken", tmp_path)


def test_page_limit_is_inclusive():
    check(opened(pdf_bytes(MAX_PAGES)))  # exactly 50 pages is fine

    with pytest.raises(UploadError, match="50 pages"):
        check(opened(pdf_bytes(MAX_PAGES + 1)))


def test_encrypted_pdfs_are_rejected_with_or_without_a_user_password():
    aes = pymupdf.PDF_ENCRYPT_AES_256
    locked = pdf_bytes(1, encryption=aes, user_pw="u", owner_pw="o")
    # opens without a password, but its owner restrictions (e.g. no copying) still apply
    restricted = pdf_bytes(1, encryption=aes, owner_pw="o")

    for data in (locked, restricted):
        with pytest.raises(UploadError, match="encrypted"):
            check(opened(data))


def test_parsing_that_exceeds_the_timeout_is_stopped(tmp_path):
    with pytest.raises(UploadError, match="took longer than"):
        ingest(pdf_bytes(2), "slow", tmp_path, timeout_s=0.001)


def test_document_ids_must_be_safe_file_names(tmp_path):
    with pytest.raises(ValueError, match="doc_id"):
        ingest(pdf_bytes(1), "../outside", tmp_path)
