"""The client's look: accent color, logo, icons, welcome photo, business card."""

from app.branding.assets import Brand, BrandError
from app.branding.colors import DEFAULT_COLOR, Palette, check_color

__all__ = ["DEFAULT_COLOR", "Brand", "BrandError", "Palette", "check_color"]
