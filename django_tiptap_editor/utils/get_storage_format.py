"""Resolve the default storage format for TipTap widgets."""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from django_tiptap_editor.constants import STORAGE_FORMAT_HTML, STORAGE_FORMATS


def get_storage_format() -> str:
    """Return ``settings.TIPTAP_STORAGE_FORMAT`` (default ``"html"``).

    Read lazily; raises ``ImproperlyConfigured`` for an unrecognised format.
    This is the default a ``TipTapWidget`` uses when no explicit ``storage=`` is
    given — ``TipTapJSONField`` always passes ``"json"`` regardless.
    """
    fmt: str = getattr(settings, "TIPTAP_STORAGE_FORMAT", STORAGE_FORMAT_HTML)
    if fmt not in STORAGE_FORMATS:
        raise ImproperlyConfigured(
            f"TIPTAP_STORAGE_FORMAT must be one of {sorted(STORAGE_FORMATS)}, got {fmt!r}."
        )
    return fmt
