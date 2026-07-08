"""Validate a (merged) TipTap config dict — fail loudly on typos."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ImproperlyConfigured

from django_tiptap_editor.constants import (
    BUILTIN_EXTENSIONS,
    ENTER_KEY_MODES,
    KNOWN_CONFIG_KEYS,
)
from django_tiptap_editor.utils.get_extra_extensions import get_extra_extensions


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    """Return ``config`` unchanged after structural validation.

    Raises ``ImproperlyConfigured`` for unknown top-level keys, an out-of-range
    ``enterKey`` value, a ``fontFamilies`` / ``fontSizes`` / ``textColors`` /
    ``highlightColors`` value that is not a list of strings, or extension names
    that are neither built in nor declared in TIPTAP_EXTRA_EXTENSIONS. Extension
    names are otherwise treated as opaque strings (resolved in JS).
    """
    unknown_keys = set(config) - KNOWN_CONFIG_KEYS
    if unknown_keys:
        raise ImproperlyConfigured(
            f"Unknown TipTap config key(s): {sorted(unknown_keys)}. "
            f"Allowed: {sorted(KNOWN_CONFIG_KEYS)}."
        )

    enter_key = config.get("enterKey")
    if enter_key is not None and enter_key not in ENTER_KEY_MODES:
        raise ImproperlyConfigured(
            f"Invalid TipTap enterKey {enter_key!r}. Allowed: {sorted(ENTER_KEY_MODES)}."
        )

    for key in ("fontFamilies", "fontSizes", "textColors", "highlightColors"):
        value = config.get(key)
        if value is not None and (
            not isinstance(value, list) or not all(isinstance(item, str) for item in value)
        ):
            raise ImproperlyConfigured(f"TipTap {key} must be a list of strings, got {value!r}.")

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
