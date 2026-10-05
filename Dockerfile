# PageSight app (Task 9.1): Gradio UI + API on port 7860. Qdrant is its own compose service; page data and the
# Hugging Face model cache are mounted at run time (docker-compose.yml, profile "app"), never baked in.
FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.22 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    HF_HOME=/hf-cache \
    HF_HUB_OFFLINE=1 \
    PAGESIGHT_HOST=0.0.0.0

WORKDIR /app
# dependencies first, so code changes reuse the cached layer (torch with CUDA 13.0, as pinned in uv.lock)
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project
COPY README.md ./
COPY src ./src
COPY configs ./configs
COPY results ./results
RUN uv sync --locked --no-dev

EXPOSE 7860
CMD ["uv", "run", "--no-sync", "python", "-m", "pagesight.ui.app"]
