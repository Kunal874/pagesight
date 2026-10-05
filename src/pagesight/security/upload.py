"""Upload safety (Task 7.3, D-040). A user's PDF is checked before anything else touches it: size and
header first, then — in a separate process, under a timeout — opening, encryption, page count and
rendering. A separate process because PyMuPDF runs in C: a Python thread cannot interrupt a PDF that
makes it hang, but the process can be killed."""

import multiprocessing
import re
from pathlib import Path

import pymupdf

from pagesight.data.pdf import render_pdf
from pagesight.data.vidore import Page

MAX_BYTES = 20 * 2**20  # 20 MB (D-040)
MAX_PAGES = 50  # D-040
# ~3x the slowest of 3 runs on the heaviest allowed upload: 6.74 s (results/upload_timing.json).
# Re-measure on the deployed hardware (Group 9): a small CPU host may be several times slower.
PARSE_TIMEOUT_S = 20.0
SAFE_ID = re.compile(r"[a-z0-9_]{1,64}")


class UploadError(ValueError):
    """The upload is refused; the message is safe to show the user."""


def check(doc: pymupdf.Document) -> None:
    # an owner-password-only PDF opens without a password; only its metadata shows the encryption
    if doc.needs_pass or (doc.metadata or {}).get("encryption"):
        raise UploadError("encrypted PDFs are not supported")
    if doc.page_count == 0:
        raise UploadError("the PDF has no pages")
    if doc.page_count > MAX_PAGES:
        raise UploadError(
            f"the PDF has {doc.page_count} pages; the limit is {MAX_PAGES} pages"
        )


def parse(pdf: Path, out_dir: Path) -> list[Page]:
    """Runs in the child process: check, then render every page at the benchmark's DPI."""
    try:
        with pymupdf.open(pdf) as doc:
            check(doc)
        return render_pdf(pdf, out_dir)
    # what PyMuPDF raises on a file it cannot read (FileDataError is a RuntimeError)
    except (RuntimeError, pymupdf.mupdf.FzErrorBase) as e:
        raise UploadError(f"malformed PDF ({type(e).__name__})") from None


def ingest(
    data: bytes, doc_id: str, out_dir: Path, timeout_s: float = PARSE_TIMEOUT_S
) -> list[Page]:
    """data: the uploaded bytes (the API reads at most MAX_BYTES + 1 of them). doc_id: chosen by
    the server, never the user's file name, because it becomes a file name."""
    if not SAFE_ID.fullmatch(doc_id):
        raise ValueError(f"doc_id must match {SAFE_ID.pattern}, got {doc_id!r}")
    if len(data) > MAX_BYTES:
        raise UploadError(f"the file is larger than {MAX_BYTES // 2**20} MB")
    # the PDF spec allows the header anywhere in the first 1,024 bytes
    if b"%PDF-" not in data[:1024]:
        raise UploadError("not a PDF file")
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf = out_dir / f"{doc_id}.pdf"
    pdf.write_bytes(data)
    # leaving the with-block terminates the worker, so a hung parse is killed, not left running.
    # ponytail: a worker that crashes outright is reported as a timeout, not as malformed.
    with multiprocessing.get_context("spawn").Pool(1) as pool:
        job = pool.apply_async(parse, (pdf, out_dir / doc_id))
        try:
            return job.get(timeout_s)
        except multiprocessing.TimeoutError:
            raise UploadError(
                f"the PDF took longer than {timeout_s:g} s to parse"
            ) from None
