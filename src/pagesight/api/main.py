"""HTTP API (Task 8.1, D-043) over the in-process service. The Gradio UI is mounted on the same app
(pagesight.ui.app), so both share one set of models.

Endpoints: GET /health · POST /search · POST /ask · POST /index-pdf (limits from Group 7, D-040)
"""

from dataclasses import asdict
from functools import lru_cache
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from pagesight.security.upload import MAX_BYTES, UploadError
from pagesight.service import Answer, Hit, PageSight

# multipart framing around the file: boundaries and part headers, a few hundred bytes in practice
FORM_OVERHEAD = 64 * 1024

app = FastAPI(title="PageSight", version="0.1.0")


@lru_cache(maxsize=1)
def get_service() -> PageSight:
    return PageSight()  # loads both models once (D-046)


Service = Annotated[PageSight, Depends(get_service)]


class SearchRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    source: str
    k: int = Field(3, ge=1, le=10)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    source: str
    mode: Literal["visual", "text"] = "visual"


def hit_json(h: Hit) -> dict:
    return {"page_id": h.page_id, "score": h.score}


def answer_json(a: Answer) -> dict:
    return {**asdict(a), "hits": [hit_json(h) for h in a.hits]}


@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    """Refuse a too-large upload from its Content-Length, before the body is received and parsed.
    A sender cannot exceed its declared length: the HTTP server rejects the extra bytes."""
    if request.url.path == "/index-pdf" and request.method == "POST":
        length = request.headers.get("content-length", "")
        if not length.isdigit():
            return JSONResponse({"detail": "Content-Length required"}, status_code=411)
        if int(length) > MAX_BYTES + FORM_OVERHEAD:
            detail = f"the file is larger than {MAX_BYTES // 2**20} MB"
            return JSONResponse({"detail": detail}, status_code=413)
    return await call_next(request)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/search")
def search(req: SearchRequest, svc: Service) -> dict:
    try:
        hits = svc.search(req.question, req.source, req.k)
    except ValueError as e:
        raise HTTPException(404, str(e)) from None
    return {"hits": [hit_json(h) for h in hits]}


@app.post("/ask")
def ask(req: AskRequest, svc: Service) -> dict:
    run = svc.ask if req.mode == "visual" else svc.ask_text
    try:
        return answer_json(run(req.question, req.source))
    except ValueError as e:
        raise HTTPException(404, str(e)) from None


@app.post("/index-pdf")
def index_pdf(file: Annotated[UploadFile, File()], svc: Service) -> dict:
    data = file.file.read(MAX_BYTES + 1)
    # a file can pass the Content-Length check by up to the form overhead
    if len(data) > MAX_BYTES:
        raise HTTPException(413, f"the file is larger than {MAX_BYTES // 2**20} MB")
    name = file.filename or "upload.pdf"
    try:
        source = svc.index_pdf(data, name)
    except UploadError as e:
        raise HTTPException(400, str(e)) from None
    return {"source": source, "name": name, "pages": len(svc.source_pages(source))}
