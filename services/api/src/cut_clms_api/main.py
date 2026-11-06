from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from cut_clms_api import __version__
from cut_clms_api.db import (
    check_database,
    create_database_engine,
    create_session_factory,
)
from cut_clms_api.endpoint_api import router as endpoint_router
from cut_clms_api.errors import install_error_handlers
from cut_clms_api.middleware import RateLimitMiddleware, RequestIDMiddleware
from cut_clms_api.settings import Settings, get_settings


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = "CUT-CLMS API"
    environment: str


class ReadinessResponse(BaseModel):
    status: Literal["ok"] = "ok"
    database: str = "ok"


class ReadinessFailure(BaseModel):
    status: Literal["unavailable"] = "unavailable"
    detail: str = "database not ready"


def create_app(
    settings: Settings | None = None, engine: Engine | None = None
) -> FastAPI:
    active_settings = settings or get_settings()
    owns_engine = engine is None
    active_engine = engine or create_database_engine(active_settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        if owns_engine:
            active_engine.dispose()

    app = FastAPI(
        title="CUT-CLMS API",
        version=__version__,
        description="Institutional computer laboratory management API.",
        lifespan=lifespan,
    )
    app.state.settings = active_settings
    app.state.engine = active_engine
    app.state.session_factory = create_session_factory(active_engine)
    app.add_middleware(
        RateLimitMiddleware,
        limit=active_settings.rate_limit_requests,
        window_seconds=active_settings.rate_limit_window_seconds,
    )
    app.add_middleware(RequestIDMiddleware)
    install_error_handlers(app)
    app.include_router(endpoint_router)

    @app.get("/healthz", response_model=HealthResponse, tags=["Operations"])
    def healthz() -> HealthResponse:
        return HealthResponse(environment=active_settings.environment)

    @app.get(
        "/readyz",
        response_model=ReadinessResponse,
        responses={503: {"model": ReadinessFailure}},
        tags=["Operations"],
    )
    def readyz() -> ReadinessResponse:
        try:
            check_database(active_engine)
        except SQLAlchemyError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="database not ready",
            ) from None
        return ReadinessResponse()

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    return app


app = create_app()
