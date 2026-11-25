FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock README.md ./

RUN uv sync --locked --no-dev --no-install-project

COPY src ./src

RUN uv sync --locked --no-dev --no-editable

FROM python:3.13-slim AS runtime

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app app

COPY --from=builder --chown=app:app /app/.venv /app/.venv

COPY --chown=app:app data/crawl.jsonl /app/data/crawl.jsonl
COPY --chown=app:app web_index.bin /app/web_index.bin

ENV PATH="/app/.venv/bin:$PATH"
ENV INDEX_PATH=/app/web_index.bin
ENV CORPUS_PATH=/app/data/crawl.jsonl
ENV PORT=8000
ENV LOG_LEVEL=INFO

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ['PORT'] + '/health')"

CMD ["python", "-m", "findex.cli", "serve"]