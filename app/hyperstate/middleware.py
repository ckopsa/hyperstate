# app/hyperstate/middleware.py

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class HyperStateMiddleware(BaseHTTPMiddleware):
    """Sets Content-Type header for HyperState responses."""

    MEDIA_TYPE = "application/vnd.hyperstate+json"

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # If the route declared hyperstate content type, ensure the header is set
        if response.headers.get("content-type", "").startswith("application/json"):
            # Check if the response body contains our type marker
            # In practice, FastAPI's response_model handles serialization;
            # we just fix the Content-Type header
            if request.url.path.startswith("/orders") or request.url.path.startswith("/api"):
                response.headers["content-type"] = f"{self.MEDIA_TYPE}; charset=utf-8"

        return response
