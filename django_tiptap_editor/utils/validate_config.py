"""Validate a (merged) TipTap config dict — fail loudly on typos."""

from __future__ import annotations

import re
from typing import Any

from django.core.exceptions import ImproperlyConfigured

from django_tiptap_editor.constants import (
    BUILTIN_EXTENSIONS,
    CSS_LENGTH_UNITS,
    ENTER_KEY_MODES,
    KNOWN_CONFIG_KEYS,
)
from django_tiptap_editor.utils.get_extra_extensions import get_extra_extensions

# The length rule for ``height`` / ``maxHeight``, mirrored by js/src/css-length.ts
# (the shared truth table is js/test/fixtures/css-lengths.json). A plain length is
# an unsigned number and a unit. A math function (calc / min / max / clamp) is
# checked lexically: every token is a number, a length, an arithmetic operator,
# a comma, whitespace, a parenthesis or one of those four functions, the
# parentheses balance and close at the very end, and at least one token is a
# length. That keeps out everything that is not arithmetic on lengths (var(),
# url(), percentages, quotes, ``;``, ``!important``); whether the arithmetic is
# well formed is left to the browser.
#
# Digits and whitespace are spelled out rather than ``\d`` / ``\s``: in Python
# those match any Unicode digit or space, so 500px in Arabic-Indic digits passed
# here while the JS side (ASCII ``\d``) and the browser refused it. Units and function names are
# ASCII case-insensitive, as in CSS; ``re.ASCII`` keeps IGNORECASE from folding
# a non-ASCII letter onto an ASCII one.
_NUMBER = r"(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:e[-+]?[0-9]+)?"
_FLAGS = re.ASCII | re.IGNORECASE
_PLAIN_LENGTH = re.compile(rf"{_NUMBER}(?P<unit>[a-z]+)", _FLAGS)
_MATH_START = re.compile(r"(?:calc|min|max|clamp)\(", _FLAGS)
_MATH_TOKEN = re.compile(
    rf"[ \t\n\r\f]+|(?:calc|min|max|clamp)?\(|\)|[-+*/,]|{_NUMBER}(?P<unit>[a-z]+)?", _FLAGS
)
_LENGTH_KEYS = ("height", "maxHeight")


def _is_css_length(value: str) -> bool:
    plain = _PLAIN_LENGTH.fullmatch(value)
    if plain is not None:
        return plain["unit"].lower() in CSS_LENGTH_UNITS
    if _MATH_START.match(value) is None:
        return False
    depth, has_length, pos = 0, False, 0
    while pos < len(value):
        token = _MATH_TOKEN.match(value, pos)
        if token is None:
            return False
        pos = token.end()
        if token[0].endswith("("):
            depth += 1
        elif token[0] == ")":
            depth -= 1
            # The outer function closed before the end: "calc(1px) + 1px". Both
            # conjuncts are held by the shared table's accepted cases: without the
            # depth check an inner group closing ("calc((100vh - 4rem) / 2)") is
            # refused, and without the position check every math function is,
            # since the outer one always closes at depth 0.
            if depth == 0 and pos < len(value):
                return False
        elif token["unit"] is not None:
            if token["unit"].lower() not in CSS_LENGTH_UNITS:
                return False
            has_length = True
    # "calc(10px" is refused by the depth check, "calc(1 + 2)" by the length one.
    return depth == 0 and has_length


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    """Return ``config`` unchanged after structural validation.

    Raises ``ImproperlyConfigured`` for unknown top-level keys, an out-of-range
    ``enterKey`` value, a ``fontFamilies`` / ``fontSizes`` / ``textColors`` /
    ``highlightColors`` / ``features`` value that is not a list of strings, a
    non-boolean ``colorPicker`` / ``imageResize``, a ``height`` / ``maxHeight`` that
    is not a CSS length (see ``_is_css_length``), ``features`` naming anything that
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

    # None and "" both read as unset, as they do in the glue, which skips a falsy
    # value: ``test_a_none_or_empty_height_reads_as_omitted`` holds both. The
    # type check is held by ``test_a_height_that_is_not_a_string_raises`` (the
    # length check would raise TypeError on a number), the length check by
    # ``test_a_string_that_is_not_a_css_length_raises``.
    for key in _LENGTH_KEYS:
        value = config.get(key)
        if value is None or value == "":
            continue
        if not isinstance(value, str) or not _is_css_length(value):
            raise ImproperlyConfigured(
                f"TipTap {key} must be a CSS length such as '400px', '30rem' or "
                f"'calc(100vh - 12rem)', got {value!r}. A bare number, 'auto' or a "
                "percentage would size the editor to nothing."
            )

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
