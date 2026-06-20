"""Resolve the import map used by external asset mode."""

from __future__ import annotations

from typing import Any

from django.conf import settings


def get_import_map() -> dict[str, Any]:
    """Return ``settings.TIPTAP_IMPORT_MAP`` (default empty).

    In external asset mode this maps bare ``@tiptap/*`` specifiers to URLs (e.g.
    a CDN), emitted as an ``importmap`` script before the glue module loads.
    """
    return getattr(settings, "TIPTAP_IMPORT_MAP", {})
