"""The upload endpoint's failure signal."""

from __future__ import annotations


class ImageUploadError(Exception):
    """Raise from ``BaseImageUploadView.save()`` to return ``400 {"error": <msg>}``."""
