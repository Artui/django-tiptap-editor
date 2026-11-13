from __future__ import annotations

import warnings
from typing import Any

from django_tiptap_editor.constants import (
    DECORATING_FEATURES,
    DEFAULT_IMAGE_PROTOCOLS,
    DEFAULT_LINK_PROTOCOLS,
    EXTENSION_HTML_VOCABULARY,
    EXTRA_ATTRIBUTE_TAGS,
    PARAGRAPH_BLOCK_TAGS,
)
from django_tiptap_editor.types.html_schema import HtmlSchema
from django_tiptap_editor.utils.get_default_config import get_default_config
from django_tiptap_editor.utils.get_extra_attributes import get_extra_attributes
from django_tiptap_editor.utils.get_extra_extensions import get_extra_extensions
from django_tiptap_editor.utils.resolve_features import resolve_features

_UNDECLARED = (
    "TipTap extension {name!r} does not declare the HTML it emits, so the server-side "
    "sanitiser will unwrap its markup and a document using it will lose the wrapper on "
    "save. Declare it as TIPTAP_EXTRA_EXTENSIONS = {{{name!r}: {{'tag': {{'attrs': "
    "['...'], 'styles': ['...']}}}}}}, or as {{{name!r}: {{}}}} if it emits no markup "
    "of its own."
)


def get_html_schema(config: dict[str, Any] | None = None) -> HtmlSchema:
    """Return the tag/attribute allowlist the editor's extensions can produce."""
    config = config or {}
    resolved = resolve_features(config)
    extras = get_extra_extensions()
    if resolved is not None:
        named = set(config.get("extensions") or ())
        builtins = [(n, v) for n, v in EXTENSION_HTML_VOCABULARY.items() if n in resolved]
        extras = {name: declared for name, declared in extras.items() if name in named}
    else:
        builtins = list(EXTENSION_HTML_VOCABULARY.items())

    vocabularies = builtins
    for name, declared in extras.items():
        if declared is None:
            warnings.warn(_UNDECLARED.format(name=name), stacklevel=2)
            continue
        vocabularies.append((name, declared))

    tags: dict[str, set[str]] = {}
    styles: dict[str, set[str]] = {}
    for decorating in (False, True):
        for name, vocabulary in vocabularies:
            if (name in DECORATING_FEATURES) is not decorating:
                continue
            for tag, entry in vocabulary.items():
                if decorating and tag not in tags:
                    continue
                tags.setdefault(tag, set()).update(entry.get("attrs", ()))
                styles.setdefault(tag, set()).update(entry.get("styles", ()))

    for node_type, names in get_extra_attributes(config or None).items():
        for tag in EXTRA_ATTRIBUTE_TAGS[node_type]:
            if tag in tags:
                tags[tag].update(names)

    protocols = get_default_config().get("linkProtocols")
    return HtmlSchema(
        tags={tag: frozenset(names) for tag, names in tags.items()},
        styles={tag: frozenset(properties) for tag, properties in styles.items()},
        link_protocols=tuple(protocols) if protocols else DEFAULT_LINK_PROTOCOLS,
        image_protocols=DEFAULT_IMAGE_PROTOCOLS,
        paragraph_blocks=frozenset() if resolved is None else PARAGRAPH_BLOCK_TAGS - set(tags),
    )
