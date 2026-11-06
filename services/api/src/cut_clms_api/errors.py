import logging
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("cut_clms_api")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid4()))


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = {
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            409: "conflict",
            429: "rate_limited",
            503: "unavailable",
            422: "invalid_request",
        }.get(exc.status_code, "request_failed")
        headers = exc.headers or {}
        return JSONResponse(
            status_code=exc.status_code,
            headers=headers,
            content={
                "error": {"code": code, "message": str(exc.detail), "details": None},
                "request_id": _request_id(request),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details: list[dict[str, Any]] = [
            {
                "location": list(error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed",
                    "details": details,
                },
                "request_id": _request_id(request),
            },
        )

    @app.exception_handler(Exception)
    async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "request failed request_id=%s exception_type=%s",
            _request_id(request),
            type(exc).__name__,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred",
                    "details": None,
                },
                "request_id": _request_id(request),
            },
        )
