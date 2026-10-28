"""The client's logo, welcome photo and home-screen icons (app/branding)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.branding.assets import Asset

router = APIRouter()

# Pages link to these files with ?v=<hash of the content>: such an address
# never changes meaning, so browsers keep it. Without the hash (the favicon,
# an icon the phone fetched earlier) it is rechecked within the hour.
FOREVER = "public, max-age=31536000, immutable"
HOUR = "public, max-age=3600"


def send(request: Request, asset: Asset | None) -> Response:
    if asset is None:
        raise HTTPException(status_code=404)
    versioned = request.query_params.get("v") == asset.version
    return Response(
        asset.body,
        media_type=asset.media_type,
        headers={"Cache-Control": FOREVER if versioned else HOUR, "ETag": f'"{asset.version}"'},
    )


# Plain def: the first call may draw the icons, which takes CPU time, so it
# runs in the thread pool rather than on the event loop.
@router.get("/app/icons/{name}", include_in_schema=False)
def icon(request: Request, name: str) -> Response:
    return send(request, request.app.state.brand.icons.get(name))


@router.get("/brand/{name}", include_in_schema=False)
async def brand_file(request: Request, name: str) -> Response:
    return send(request, request.app.state.brand.files.get(name))
