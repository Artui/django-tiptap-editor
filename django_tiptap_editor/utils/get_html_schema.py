"""Build the HTML allowlist from the extensions the editor mounts."""

from __future__ import annotations

import warnings

from django_tiptap_editor.constants import (
    DEFAULT_IMAGE_PROTOCOLS,
    DEFAULT_LINK_PROTOCOLS,
    EXTENSION_HTML_VOCABULARY,
)
from django_tiptap_editor.types.html_schema import HtmlSchema
from django_tiptap_editor.utils.get_default_config import get_default_config
from django_tiptap_editor.utils.get_extra_extensions import get_extra_extensions

_UNDECLARED = (
    "TipTap extension {name!r} does not declare the HTML it emits, so the server-side "
    "sanitiser will unwrap its markup and a document using it will lose the wrapper on "
    "save. Declare it as TIPTAP_EXTRA_EXTENSIONS = {{{name!r}: {{'tag': {{'attrs': "
    "['...'], 'styles': ['...']}}}}}}, or as {{{name!r}: {{}}}} if it emits no markup "
    "of its own."
)


def get_html_schema() -> HtmlSchema:
    """Return the tag/attribute allowlist the editor's extensions can produce.

    The vocabulary is the union of ``EXTENSION_HTML_VOCABULARY`` -- one entry per
    built-in extension -- plus whatever ``TIPTAP_EXTRA_EXTENSIONS`` declares. The
    built-ins are always part of it because the JS glue mounts the whole baseline
    on every editor; a per-widget ``extensions`` list only *adds* consumer
    extensions, and ``validate_config`` already refuses a name that is neither
    built in nor registered. So this is the complete set of markup any editor in
    the project can emit, which is what makes it the right allowlist to enforce.

    A registered extension whose vocabulary is undeclared warns, naming it: the
    sanitiser cannot keep markup nobody has described, and losing it silently is
    how a custom node disappears from a document on its first save.
    """
    tags: dict[str, set[str]] = {}
    styles: dict[str, set[str]] = {}
    vocabularies = list(EXTENSION_HTML_VOCABULARY.items())
    for name, declared in get_extra_extensions().items():
        if declared is None:
            warnings.warn(_UNDECLARED.format(name=name), stacklevel=2)
            continue
        vocabularies.append((name, declared))

    for _name, vocabulary in vocabularies:
        for tag, entry in vocabulary.items():
            tags.setdefault(tag, set()).update(entry.get("attrs", ()))
            styles.setdefault(tag, set()).update(entry.get("styles", ()))

    protocols = get_default_config().get("linkProtocols")
    return HtmlSchema(
        tags={tag: frozenset(names) for tag, names in tags.items()},
        styles={tag: frozenset(properties) for tag, properties in styles.items()},
        link_protocols=tuple(protocols) if protocols else DEFAULT_LINK_PROTOCOLS,
        image_protocols=DEFAULT_IMAGE_PROTOCOLS,
    )
