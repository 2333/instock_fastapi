from collections.abc import Callable

from fastapi import APIRouter, Request
from starlette.middleware.base import BaseHTTPMiddleware

router = APIRouter()


class APIVersioningMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path

        if path.startswith("/api/"):
            if path.startswith("/api/v1/"):
                request.state.api_version = "v1"
            elif path.startswith("/api/v2/"):
                request.state.api_version = "v2"
            else:
                request.state.api_version = "unknown"

            if request.state.api_version == "unknown":
                from fastapi.responses import JSONResponse

                from app.exceptions import error_response

                return JSONResponse(
                    status_code=404,
                    content=error_response("API_VERSION_NOT_FOUND", "API version not supported"),
                )

        response = await call_next(request)

        if hasattr(request.state, "api_version"):
            response.headers["X-API-Version"] = request.state.api_version

        return response


def add_version_headers(response):
    pass
