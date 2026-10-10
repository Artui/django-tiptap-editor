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
    ``highlightColors`` / ``features`` value that is not a list of strings, a
    non-boolean ``colorPicker`` / ``imageResize``, ``features`` naming anything that
    is not a built-in extension, or extension names that are neither built in nor
    declared in TIPTAP_EXTRA_EXTENSIONS. Extension names are otherwise treated as
    opaque strings (resolved in JS).

    ``features`` accepts built-in names only: it restricts the editor's own
    extensions, and a custom one is switched on by listing it in ``extensions``.
    Core names (``FEATURE_CORE``) are accepted and change nothing, since core is
    always on. ``None`` reads as omitted, like every other key here.
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

    # Each conjunct below is held by a test: the list check by
    # ``test_string_list_not_a_list_raises`` / ``test_features_not_a_list_raises``
    # (a bare string passes the member check character by character), the member
    # check by ``test_string_list_with_non_string_item_raises`` /
    # ``test_features_with_a_non_string_member_raises``. For ``features`` it also
    # has to run before the name lookup below, which would raise ``TypeError`` on
    # an unhashable member rather than ``ImproperlyConfigured``.
    for key in ("fontFamilies", "fontSizes", "textColors", "highlightColors", "features"):
        value = config.get(key)
        if value is not None and (
            not isinstance(value, list) or not all(isinstance(item, str) for item in value)
        ):
            raise ImproperlyConfigured(f"TipTap {key} must be a list of strings, got {value!r}.")

    for key in ("colorPicker", "imageResize"):
        value = config.get(key)
        if value is not None and not isinstance(value, bool):
            raise ImproperlyConfigured(f"TipTap {key} must be a boolean, got {value!r}.")

    features = config.get("features")
    if features is not None:
        unknown_features = [name for name in features if name not in BUILTIN_EXTENSIONS]
        if unknown_features:
            raise ImproperlyConfigured(
                f"Unknown TipTap feature(s): {unknown_features}. Allowed: "
                f"{sorted(BUILTIN_EXTENSIONS)}. Custom extensions go in `extensions`."
            )

    extensions = config.get("extensions")
    if extensions is not None:
        allowed = BUILTIN_EXTENSIONS | frozenset(get_extra_extensions())
        unknown_ext = [name for name in extensions if name not in allowed]
        if unknown_ext:
            raise ImproperlyConfigured(
                f"Unknown TipTap extension(s): {unknown_ext}. Register them in JS and "
                f"add their names to TIPTAP_EXTRA_EXTENSIONS."
            )
    return config
