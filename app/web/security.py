"""Cross-site request protection for the JSON API.

The owner's session cookie is SameSite=Lax, which already keeps it off
cross-site POSTs. As a second lock, any state-changing API request that
carries an Origin header must come from this same host.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

from fastapi import Request, Response
from fastapi.responses import JSONResponse

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


async def same_origin_only(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    if request.method in UNSAFE_METHODS and request.url.path.startswith("/api/"):
        origin = request.headers.get("origin")
        if origin and urlsplit(origin).netloc != request.headers.get("host"):
            return JSONResponse({"error": "cross_origin"}, status_code=403)
    return await call_next(request)
