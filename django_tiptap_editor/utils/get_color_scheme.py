from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from django_tiptap_editor.constants import COLOR_SCHEMES


def get_color_scheme() -> str | None:
    """Return ``settings.TIPTAP_COLOR_SCHEME``, or ``None`` when it is unset."""
    scheme: Any = getattr(settings, "TIPTAP_COLOR_SCHEME", None)
    if scheme is not None and (not isinstance(scheme, str) or scheme not in COLOR_SCHEMES):
        raise ImproperlyConfigured(
            f"TIPTAP_COLOR_SCHEME must be one of {sorted(COLOR_SCHEMES)}, got {scheme!r}."
        )
    return scheme
