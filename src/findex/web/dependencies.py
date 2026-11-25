from fastapi import HTTPException, Request

from findex.index import Index
from findex.web.settings import Settings


def get_settings(request: Request) -> Settings:
    settings: object = request.app.state.settings

    if not isinstance(settings, Settings):
        raise TypeError("Invalid application settings")

    return settings


def get_index(request: Request) -> Index:
    index: object = getattr(request.app.state, "index", None)

    if not isinstance(index, Index):
        raise HTTPException(
            status_code=503,
            detail="Index is not loaded",
        )

    return index
