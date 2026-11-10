from __future__ import annotations

from typing import Any

from django.conf import settings

from django_tiptap_editor.constants import DEFAULT_CONFIG


def get_default_config() -> dict[str, Any]:
    """Return ``DEFAULT_CONFIG`` merged with ``settings.TIPTAP_DEFAULT_CONFIG``."""
    override: dict[str, Any] = getattr(settings, "TIPTAP_DEFAULT_CONFIG", {})
    return {**DEFAULT_CONFIG, **override}
