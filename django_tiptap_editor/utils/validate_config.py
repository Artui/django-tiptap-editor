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
from django_tiptap_editor.utils.get_extra_attributes import get_extra_attributes
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
            # The outer function closed before the end: "calc(1px) + 1px".
            if depth == 0 and pos < len(value):
                return False
        elif token["unit"] is not None:
            if token["unit"].lower() not in CSS_LENGTH_UNITS:
                return False
            has_length = True
    return depth == 0 and has_length


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    """Return ``config`` unchanged after structural validation."""
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
    ceiling = get_extra_attributes()
    wider = [
        f"{node_type}.{name}"
        for node_type, names in get_extra_attributes(config).items()
        for name in names
        if name not in ceiling.get(node_type, ())
    ]
    if wider:
        raise ImproperlyConfigured(
            f"TipTap extraAttributes grants {wider} beyond TIPTAP_DEFAULT_CONFIG's "
            f"extraAttributes. A field may narrow the project grant, not widen it: the "
            f"html mirror and the tiptap_html filter render without a field config."
        )
    return config
