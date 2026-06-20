"""Resolve the import map used by external asset mode."""

from __future__ import annotations

from typing import Any

from django.conf import settings

from django_tiptap_editor.constants import ESM_CDN, GLUE_IMPORT_SPECIFIERS, TIPTAP_VERSION


def default_import_map() -> dict[str, str]:
    """Pin every glue specifier to the validated TipTap version on the CDN."""
    return {spec: f"{ESM_CDN}/{spec}@{TIPTAP_VERSION}" for spec in GLUE_IMPORT_SPECIFIERS}


def get_import_map() -> dict[str, Any]:
    """Return ``settings.TIPTAP_IMPORT_MAP``, or a known-good default.

    In external asset mode this maps bare ``@tiptap/*`` specifiers to URLs,
    emitted as an ``importmap`` script before the glue module loads. The default
    pins each specifier to the validated TipTap version on a CDN; the consumer
    overrides deliberately (e.g. to self-host or use a different TipTap build).
    """
    configured = getattr(settings, "TIPTAP_IMPORT_MAP", None)
    if configured is not None:
        return configured
    return default_import_map()
