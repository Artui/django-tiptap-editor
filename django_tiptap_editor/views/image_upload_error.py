"""Error a custom upload view raises to return a 400 to the editor."""

from __future__ import annotations


class ImageUploadError(Exception):
    """Raise from ``BaseImageUploadView.save()`` to return ``400 {"error": <msg>}``."""
