# app/hyperstate/middleware.py

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


import os

class HyperStateMiddleware(BaseHTTPMiddleware):
    """Sets Content-Type header for HyperState responses. Serves HTML client for UI paths if not requesting JSON."""

    MEDIA_TYPE = "application/vnd.hyperstate+json"

    async def dispatch(self, request: Request, call_next):
        # Determine if client is requesting the SPA HTML
        accept_header = request.headers.get("accept", "")
        is_html_request = "text/html" in accept_header and self.MEDIA_TYPE not in accept_header

        # Paths that shouldn't serve the SPA HTML
        api_prefixes = ("/api", "/docs", "/openapi.json", "/uploads")

        if is_html_request and request.method == "GET" and not request.url.path.startswith(api_prefixes):
            # Serve the SPA client.html instead of proceeding to the API route
            # This allows clean URLs like /lessons/LES-123 to load the SPA
            file_path = os.path.join(os.path.dirname(__file__), "..", "web", "client.html")
            try:
                with open(file_path, "r") as f:
                    content = f.read()
                return Response(content=content, media_type="text/html")
            except FileNotFoundError:
                pass

        response: Response = await call_next(request)

        # If the route declared hyperstate content type, ensure the header is set
        if response.headers.get("content-type", "").startswith("application/json"):
            # Ensure the Content-Type header is updated for all HyperState responses,
            # not just a specific subset of endpoints.
            response.headers["content-type"] = f"{self.MEDIA_TYPE}; charset=utf-8"

        return response
