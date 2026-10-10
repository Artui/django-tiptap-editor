"""Build the HTML allowlist from the extensions the editor mounts."""

from __future__ import annotations

import warnings
from typing import Any

from django_tiptap_editor.constants import (
    DECORATING_FEATURES,
    DEFAULT_IMAGE_PROTOCOLS,
    DEFAULT_LINK_PROTOCOLS,
    EXTENSION_HTML_VOCABULARY,
    PARAGRAPH_BLOCK_TAGS,
)
from django_tiptap_editor.types.html_schema import HtmlSchema
from django_tiptap_editor.utils.get_default_config import get_default_config
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
    """Return the tag/attribute allowlist the editor's extensions can produce.

    Without a ``features`` list in ``config`` (or with no config at all) the
    vocabulary is the union of ``EXTENSION_HTML_VOCABULARY`` -- one entry per
    built-in extension -- plus whatever ``TIPTAP_EXTRA_EXTENSIONS`` declares. The
    built-ins are all part of it because the JS glue mounts the whole baseline on
    an unrestricted editor; a per-widget ``extensions`` list only *adds* consumer
    extensions, and ``validate_config`` already refuses a name that is neither
    built in nor registered. So this is the complete set of markup any
    unrestricted editor in the project can emit, which is what makes it the right
    allowlist to enforce there.

    A ``features`` list narrows it to what that field's editor mounts: the
    vocabularies of ``resolve_features(config)``, and of the custom extensions the
    config's own ``extensions`` list names (one it does not name is not mounted,
    so its markup is not kept). A feature in ``DECORATING_FEATURES`` adds its
    attributes and style properties to tags another feature admits, never a tag
    of its own. Built-in blocks left out are listed in ``paragraph_blocks``, which
    the sanitiser turns into paragraph boundaries.

    A registered extension whose vocabulary is undeclared warns, naming it, when
    it is part of the allowlist being built: the sanitiser cannot keep markup
    nobody has described, and losing it silently is how a custom node disappears
    from a document on its first save.
    """
    config = config or {}
    resolved = resolve_features(config)
    extras = get_extra_extensions()
    if resolved is not None:
        # Each guard has a test that fails without it: "admit only the
        # vocabularies of the resolved set" (the features filter) and "takes only
        # the extensions its config names" (the extras filter), both in
        # tests/utils/test_get_html_schema.py.
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
    # Tags first, then the decorations onto the tags that made it: an attribute
    # feature's vocabulary only ever narrows onto something already admitted.
    # Unrestricted, every tag a decorating feature names is admitted by another
    # built-in anyway, so the two passes build exactly the old union.
    for decorating in (False, True):
        for name, vocabulary in vocabularies:
            if (name in DECORATING_FEATURES) is not decorating:
                continue
            for tag, entry in vocabulary.items():
                if decorating and tag not in tags:
                    continue
                tags.setdefault(tag, set()).update(entry.get("attrs", ()))
                styles.setdefault(tag, set()).update(entry.get("styles", ()))

    protocols = get_default_config().get("linkProtocols")
    return HtmlSchema(
        tags={tag: frozenset(names) for tag, names in tags.items()},
        styles={tag: frozenset(properties) for tag, properties in styles.items()},
        link_protocols=tuple(protocols) if protocols else DEFAULT_LINK_PROTOCOLS,
        image_protocols=DEFAULT_IMAGE_PROTOCOLS,
        paragraph_blocks=frozenset() if resolved is None else PARAGRAPH_BLOCK_TAGS - set(tags),
    )
