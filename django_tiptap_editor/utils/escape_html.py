"""HTML escaping shared by the renderer and the sanitiser (internal helper)."""

from __future__ import annotations


def escape_html(value: str, *, quote: bool = False) -> str:
    """Escape ``value`` for HTML text, or for a double-quoted attribute value.

    Escapes ``&``, ``<`` and ``>``; ``quote=True`` also escapes ``"``. It stops
    there on purpose: an apostrophe is inert both in text and inside a
    double-quoted attribute, and Django's ``escape`` rewriting it to ``&#x27;``
    would make every apostrophe in an author's prose change on save. Escaping
    exactly what a browser's own serialiser escapes is what lets a document
    round-trip byte-identically through the sanitiser.
    """
    escaped = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return escaped.replace('"', "&quot;") if quote else escaped
