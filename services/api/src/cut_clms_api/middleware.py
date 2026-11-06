from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        *,
        limit: int,
        window_seconds: int,
        path_prefix: str = "/api/v1/endpoints/",
    ) -> None:
        super().__init__(app)
        self.limit = limit
        self.window_seconds = window_seconds
        self.path_prefix = path_prefix
        self._requests: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = Lock()
        self._checks = 0

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not request.url.path.startswith(self.path_prefix):
            return await call_next(request)
        host = request.client.host if request.client else "unknown"
        key = (host, request.url.path)
        now = monotonic()
        with self._lock:
            self._checks += 1
            if self._checks % 256 == 0:
                stale_keys = [
                    stored_key
                    for stored_key, stored_requests in self._requests.items()
                    if not stored_requests
                    or now - stored_requests[-1] >= self.window_seconds
                ]
                for stale_key in stale_keys:
                    del self._requests[stale_key]
            requests = self._requests[key]
            while requests and now - requests[0] >= self.window_seconds:
                requests.popleft()
            if len(requests) >= self.limit:
                retry_after = max(1, int(self.window_seconds - (now - requests[0])))
                return JSONResponse(
                    status_code=429,
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(self.limit),
                    },
                    content={
                        "error": {
                            "code": "rate_limited",
                            "message": "Rate limit exceeded",
                            "details": None,
                        },
                        "request_id": getattr(
                            request.state, "request_id", str(uuid4())
                        ),
                    },
                )
            requests.append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        return response
