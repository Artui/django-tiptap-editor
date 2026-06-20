"""Resolve the active asset delivery mode."""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from django_tiptap_editor.constants import ASSET_MODE_BUNDLE, ASSET_MODES


def get_asset_mode() -> str:
    """Return ``settings.TIPTAP_ASSET_MODE`` (default ``"bundle"``).

    Raises ``ImproperlyConfigured`` for an unrecognised mode.
    """
    mode: str = getattr(settings, "TIPTAP_ASSET_MODE", ASSET_MODE_BUNDLE)
    if mode not in ASSET_MODES:
        raise ImproperlyConfigured(
            f"TIPTAP_ASSET_MODE must be one of {sorted(ASSET_MODES)}, got {mode!r}."
        )
    return mode
