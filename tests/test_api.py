"""API smoke tests (Task 8.4): the real FastAPI app over the CPU fake service (tests/conftest.py)."""

import warnings

import pytest

from pagesight.api.main import FORM_OVERHEAD, app, get_service

# Starlette 1.7 asks for httpx2, which is not on our approved list
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", "Using `httpx` with `starlette.testclient`")
    from fastapi.testclient import TestClient

pytestmark = pytest.mark.filterwarnings("ignore:Local mode performs exact")


@pytest.fixture
def client(service):
    app.dependency_overrides[get_service] = lambda: service
    yield TestClient(app)
    app.dependency_overrides.clear()


def upload(client, data: bytes, name: str = "report.pdf"):
    return client.post("/index-pdf", files={"file": (name, data, "application/pdf")})


def test_health_answers_without_loading_models():
    # no override: a health check must never trigger the model load
    assert TestClient(app).get("/health").json() == {"status": "ok"}


def test_upload_search_and_ask_end_to_end(client, make_pdf):
    up = upload(client, make_pdf("alpha revenue", "beta costs"))
    assert up.status_code == 200
    source = up.json()["source"]
    assert up.json() == {"source": source, "name": "report.pdf", "pages": 2}

    hits = client.post("/search", json={"question": "beta", "source": source, "k": 2})
    assert [h["page_id"] for h in hits.json()["hits"]] == [f"{source}-1", f"{source}-0"]

    answer = client.post("/ask", json={"question": "beta", "source": source}).json()
    assert answer["mode"] == "visual" and answer["status"] == "answer"
    assert answer["citations"] == [f"{source}-1"] and answer["text"] == "It is 42."


def test_ask_in_text_mode_uses_bm25(client, make_pdf):
    source = upload(client, make_pdf("alpha revenue", "beta costs")).json()["source"]

    answer = client.post(
        "/ask", json={"question": "beta costs", "source": source, "mode": "text"}
    ).json()

    assert answer["mode"] == "text" and answer["shown"][0] == f"{source}-1"


def test_a_refused_upload_is_a_400_with_the_reason(client):
    response = upload(client, b"<html>hello</html>", "page.pdf")

    assert response.status_code == 400
    assert response.json()["detail"] == "not a PDF file"


def test_an_oversized_upload_is_a_413_before_the_body_is_parsed(client, monkeypatch):
    monkeypatch.setattr("pagesight.api.main.MAX_BYTES", 1_000)

    response = upload(client, b"%PDF-1.7\n" + b"0" * (1_000 + FORM_OVERHEAD))

    assert response.status_code == 413


def test_unknown_sources_are_404(client):
    response = client.post("/ask", json={"question": "beta", "source": "nope"})

    assert response.status_code == 404


def test_empty_questions_are_rejected(client):
    response = client.post("/search", json={"question": "", "source": "hr"})

    assert response.status_code == 422


def test_an_upload_without_a_content_length_is_refused_unread(client):
    # a streamed (chunked) body declares no length, so its size cannot be checked up front
    def body():
        yield b"--x\r\n"

    headers = {"content-type": "multipart/form-data; boundary=x"}
    response = client.post("/index-pdf", content=body(), headers=headers)

    assert response.status_code == 411
