"""Re-encoding uploaded photos.

The browser already shrinks photos before upload, but the server does not
trust that. Every photo is decoded and written out again as a plain JPEG:
- metadata is dropped, including GPS coordinates phones embed in EXIF, which
  would reveal where the seller lives;
- the orientation from EXIF is applied first, so photos stay upright;
- anything that is not really an image fails here instead of being stored.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

ACCEPTED_FORMATS = {"JPEG", "MPO", "PNG", "WEBP"}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
# Decompression bomb guard: a few kilobytes of PNG can claim gigapixels.
MAX_PIXELS = 50_000_000
FULL_SIZE = 1600
THUMB_SIZE = 480


class ImageRejected(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ProcessedImage:
    full: bytes
    thumb: bytes
    width: int
    height: int


def _jpeg(image: Image.Image, size: int, quality: int) -> bytes:
    copy = image.copy()
    copy.thumbnail((size, size), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    copy.save(buffer, "JPEG", quality=quality, optimize=True, progressive=True)
    return buffer.getvalue()


def process_upload(data: bytes) -> ProcessedImage:
    if len(data) > MAX_UPLOAD_BYTES:
        raise ImageRejected("too_large")
    try:
        with Image.open(io.BytesIO(data)) as source:
            if source.format not in ACCEPTED_FORMATS:
                raise ImageRejected("format")
            if source.width * source.height > MAX_PIXELS:
                raise ImageRejected("too_large")
            image = ImageOps.exif_transpose(source).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ImageRejected("format") from exc

    full = _jpeg(image, FULL_SIZE, quality=82)
    with Image.open(io.BytesIO(full)) as stored:
        width, height = stored.size
    return ProcessedImage(
        full=full, thumb=_jpeg(image, THUMB_SIZE, quality=75), width=width, height=height
    )
