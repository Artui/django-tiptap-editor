"""Resolve consumer-registered extension names for config validation."""

from __future__ import annotations

from django.conf import settings


def get_extra_extensions() -> frozenset[str]:
    """Return ``settings.TIPTAP_EXTRA_EXTENSIONS`` (default empty) as a set.

    These augment the built-in allowlist so consumer-registered extensions pass
    Python validation.
    """
    extras: list[str] = getattr(settings, "TIPTAP_EXTRA_EXTENSIONS", [])
    return frozenset(extras)
