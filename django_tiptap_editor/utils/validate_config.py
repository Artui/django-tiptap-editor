"""Validate a (merged) TipTap config dict — fail loudly on typos."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ImproperlyConfigured

from django_tiptap_editor.constants import BUILTIN_EXTENSIONS, KNOWN_CONFIG_KEYS
from django_tiptap_editor.utils.get_extra_extensions import get_extra_extensions


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    """Return ``config`` unchanged after structural validation.

    Raises ``ImproperlyConfigured`` for unknown top-level keys, or for extension
    names that are neither built in nor declared in TIPTAP_EXTRA_EXTENSIONS.
    Extension names are otherwise treated as opaque strings (resolved in JS).
    """
    unknown_keys = set(config) - KNOWN_CONFIG_KEYS
    if unknown_keys:
        raise ImproperlyConfigured(
            f"Unknown TipTap config key(s): {sorted(unknown_keys)}. "
            f"Allowed: {sorted(KNOWN_CONFIG_KEYS)}."
        )

    extensions = config.get("extensions")
    if extensions is not None:
        allowed = BUILTIN_EXTENSIONS | get_extra_extensions()
        unknown_ext = [name for name in extensions if name not in allowed]
        if unknown_ext:
            raise ImproperlyConfigured(
                f"Unknown TipTap extension(s): {unknown_ext}. Register them in JS and "
                f"add their names to TIPTAP_EXTRA_EXTENSIONS."
            )
    return config
