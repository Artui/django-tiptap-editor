"""Resolve consumer-registered extensions and the HTML vocabulary they emit."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from django_tiptap_editor.constants import FORBIDDEN_TAGS, VOCABULARY_KEYS

_TAG_RE = re.compile(r"^[a-z][a-z0-9-]*$")

Vocabulary = dict[str, dict[str, tuple[str, ...]]]


def _tokens(value: Any, name: str, tag: str, key: str) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise ImproperlyConfigured(
            f"TIPTAP_EXTRA_EXTENSIONS[{name!r}][{tag!r}][{key!r}] must be a list of "
            f"strings, got {value!r}."
        )
    tokens = tuple(str(item).lower() for item in value)
    forbidden = [token for token in tokens if key == "attrs" and token.startswith("on")]
    if forbidden:
        raise ImproperlyConfigured(
            f"TIPTAP_EXTRA_EXTENSIONS[{name!r}][{tag!r}] declares event-handler "
            f"attribute(s) {forbidden}. An on* attribute is script; a custom "
            f"extension cannot opt out of that."
        )
    return tokens


def _vocabulary(name: str, declared: Any) -> Vocabulary:
    if not isinstance(declared, Mapping):
        raise ImproperlyConfigured(
            f"TIPTAP_EXTRA_EXTENSIONS[{name!r}] must map a tag name to its "
            f"{{'attrs': [...], 'styles': [...]}} vocabulary, got {declared!r}."
        )
    vocabulary: Vocabulary = {}
    for tag, entry in declared.items():
        tag = str(tag).lower()
        if not _TAG_RE.match(tag):
            raise ImproperlyConfigured(
                f"TIPTAP_EXTRA_EXTENSIONS[{name!r}] declares an invalid tag {tag!r}."
            )
        if tag in FORBIDDEN_TAGS:
            raise ImproperlyConfigured(
                f"TIPTAP_EXTRA_EXTENSIONS[{name!r}] declares the tag {tag!r}, which "
                f"executes script or loads a document. Allowing it would defeat the "
                f"sanitiser. Forbidden: {sorted(FORBIDDEN_TAGS)}."
            )
        if not isinstance(entry, Mapping) or set(entry) - VOCABULARY_KEYS:
            raise ImproperlyConfigured(
                f"TIPTAP_EXTRA_EXTENSIONS[{name!r}][{tag!r}] must be a mapping with "
                f"keys {sorted(VOCABULARY_KEYS)}, got {entry!r}."
            )
        vocabulary[tag] = {key: _tokens(entry[key], name, tag, key) for key in entry if entry[key]}
    return vocabulary


def get_extra_extensions() -> dict[str, Vocabulary | None]:
    """Return ``settings.TIPTAP_EXTRA_EXTENSIONS`` as name -> HTML vocabulary.

    These augment the built-in allowlist so consumer-registered extensions pass
    Python validation. Two forms are accepted:

    * a list of names -- the extension is recognised but its vocabulary is
      undeclared (``None``), so ``get_html_schema`` warns and the sanitiser
      unwraps its tags;
    * a mapping of name to ``{tag: {"attrs": [...], "styles": [...]}}`` -- the
      extension declares its own vocabulary, which joins the allowlist so its
      markup survives sanitisation intact.

    Raises ``ImproperlyConfigured`` for a malformed declaration, for a tag that
    executes script, and for an ``on*`` attribute.
    """
    extras: Any = getattr(settings, "TIPTAP_EXTRA_EXTENSIONS", [])
    if isinstance(extras, Mapping):
        return {str(name): _vocabulary(str(name), declared) for name, declared in extras.items()}
    return {str(name): None for name in extras}
