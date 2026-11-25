import asyncio
import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from time import monotonic, perf_counter
from typing import Annotated, Literal, cast
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response

from findex.corpus import iter_documents
from findex.index import Index
from findex.ranking import search as ranked_search
from findex.scoring import get_scorer
from findex.snippets import snippet_from_text
from findex.store import load
from findex.web.dependencies import get_index, get_settings
from findex.web.models import (
    DocumentResponse,
    HealthResponse,
    SearchResponse,
    SearchResult,
    StatsResponse,
)
from findex.web.settings import Settings

logger = logging.getLogger(__name__)


def load_documents(settings: Settings) -> dict[str, str]:
    return {
        document.path: document.text
        for document in iter_documents(settings.corpus_path)
    }


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings = Settings()

    logging.basicConfig(
        level=settings.log_level.upper(),
    )

    app.state.settings = settings
    app.state.started_at = monotonic()
    app.state.index = None
    app.state.documents = {}
    app.state.index_size = 0

    try:
        app.state.index = await asyncio.to_thread(
            load,
            settings.index_path,
        )

        app.state.documents = await asyncio.to_thread(
            load_documents,
            settings,
        )

        app.state.index_size = settings.index_path.stat().st_size

        logger.info("Index loaded successfully")

    except Exception:
        app.state.index = None
        logger.exception("Failed to load index")

    try:
        yield
    finally:
        app.state.index = None
        app.state.documents = {}


app = FastAPI(
    title="Findex Search API",
    version="0.7.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_logging(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = str(uuid4())

    try:
        response = await call_next(request)

    except Exception:
        logger.exception(
            "Unexpected error request_id=%s",
            request_id,
        )

        response = JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    response.headers["X-Request-ID"] = request_id

    logger.info(
        "request_id=%s method=%s path=%s status=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
    )

    return response


def document_text(
    request: Request,
    index: Index,
    doc_id: int,
) -> str:
    documents = cast(
        dict[str, str],
        getattr(request.app.state, "documents", {}),
    )

    path = index.doc_meta[doc_id].path

    return documents.get(path, "")


@app.get("/search", response_model=SearchResponse)
def search(
    request: Request,
    index: Annotated[Index, Depends(get_index)],
    q: Annotated[str, Query(min_length=1, max_length=200)],
    k: Annotated[int, Query(ge=1, le=100)] = 10,
    scorer: Literal["bm25", "tfidf"] = "bm25",
    page: Annotated[int, Query(ge=1)] = 1,
) -> SearchResponse:
    start = perf_counter()

    if not q.strip():
        raise HTTPException(
            status_code=422,
            detail="Query cannot be empty",
        )

    try:
        ranked = ranked_search(
            index,
            q,
            get_scorer(scorer),
            index.num_docs,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    offset = (page - 1) * k

    results = [
        SearchResult(
            doc_id=item.doc_id,
            title=item.title,
            score=item.score,
            snippet=snippet_from_text(
                document_text(request, index, item.doc_id),
                q,
            ),
        )
        for item in ranked[offset : offset + k]
    ]

    return SearchResponse(
        query=q,
        total=len(ranked),
        took_ms=(perf_counter() - start) * 1000,
        results=results,
    )


@app.get("/docs/{doc_id}", response_model=DocumentResponse)
def get_document(
    doc_id: int,
    request: Request,
    index: Annotated[Index, Depends(get_index)],
) -> DocumentResponse:
    if doc_id not in index.doc_meta:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    meta = index.doc_meta[doc_id]

    return DocumentResponse(
        doc_id=doc_id,
        title=meta.title,
        path=meta.path,
        text=document_text(request, index, doc_id),
    )


@app.get("/stats", response_model=StatsResponse)
def stats(
    request: Request,
    index: Annotated[Index, Depends(get_index)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> StatsResponse:
    started_at = cast(
        float,
        getattr(request.app.state, "started_at", monotonic()),
    )

    return StatsResponse(
        index_size=cast(
            int,
            getattr(request.app.state, "index_size", 0),
        ),
        doc_count=index.num_docs,
        vocabulary=len(index),
        uptime=monotonic() - started_at,
    )


@app.get("/health", response_model=HealthResponse)
def health(
    index: Annotated[Index, Depends(get_index)],
) -> HealthResponse:
    return HealthResponse(status="ok")


from pathlib import Path

from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

WEB_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(
    directory=str(WEB_DIR / "templates"),
)

app.mount(
    "/static",
    StaticFiles(directory=str(WEB_DIR / "static")),
    name="static",
)


@app.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    index: Annotated[Index, Depends(get_index)],
    q: Annotated[str, Query(max_length=200)] = "",
    page: Annotated[int, Query(ge=1)] = 1,
) -> Response:
    result = None

    if q.strip():
        result = search(
            request=request,
            index=index,
            q=q,
            k=10,
            scorer="bm25",
            page=page,
        )

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "q": q,
            "page": page,
            "result": result,
        },
    )


@app.get("/doc/{doc_id}", response_class=HTMLResponse)
def document_page(
    doc_id: int,
    request: Request,
    index: Annotated[Index, Depends(get_index)],
) -> Response:
    document = get_document(
        doc_id=doc_id,
        request=request,
        index=index,
    )

    return templates.TemplateResponse(
        request=request,
        name="document.html",
        context={"document": document},
    )
