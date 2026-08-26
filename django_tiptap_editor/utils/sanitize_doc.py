"""Pure-Python protocol allowlisting for a stored ProseMirror document.

JSON storage means a document can be written by something other than the editor
(an API, an import, a hand-edit). ProseMirror's schema only allowlists protocols
on *parse*, which a stored-JSON path never runs — so a doc could carry a
``javascript:`` link ``href`` or image ``src``. This walks the tree and strips
any URL whose scheme is outside the allowlist (relative / anchor URLs, having no
scheme, are always kept), before the value is persisted.

Deliberately narrow: it secures the URL-bearing attributes and bounds the
nesting, not the full schema. Structural validation is the editor's job.
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError

from django_tiptap_editor.constants import (
    DEFAULT_IMAGE_PROTOCOLS,
    DEFAULT_LINK_PROTOCOLS,
    MAX_DOCUMENT_DEPTH,
)
from django_tiptap_editor.utils.is_allowed_url import is_allowed_url


def sanitize_doc(
    doc: Any,
    *,
    link_protocols: tuple[str, ...] = DEFAULT_LINK_PROTOCOLS,
    image_protocols: tuple[str, ...] = DEFAULT_IMAGE_PROTOCOLS,
) -> Any:
    """Return a copy of ``doc`` with disallowed link/image URLs stripped.

    A node's ``image`` ``src`` outside ``image_protocols`` is blanked; a ``link``
    mark whose ``href`` is outside ``link_protocols`` is dropped. Non-dict input
    is returned unchanged (the field validates structure separately).

    Raises ``ValidationError`` for a document nested deeper than
    ``MAX_DOCUMENT_DEPTH``. Both this walk and the renderer's recurse per level,
    so an unbounded document is a few kilobytes that costs the process its
    stack; refusing it here turns a 500 into a field error.
    """
    return _sanitize(doc, link_protocols, image_protocols, 0)


def _sanitize(
    doc: Any,
    link_protocols: tuple[str, ...],
    image_protocols: tuple[str, ...],
    depth: int,
) -> Any:
    if not isinstance(doc, dict):
        return doc
    if depth >= MAX_DOCUMENT_DEPTH:
        raise ValidationError(
            f"TipTap document nests deeper than the maximum of {MAX_DOCUMENT_DEPTH} nodes."
        )

    node: dict[str, Any] = {**doc}

    if node.get("type") == "image":
        attrs = node.get("attrs")
        if isinstance(attrs, dict) and not is_allowed_url(attrs.get("src"), image_protocols):
            node["attrs"] = {**attrs, "src": ""}

    marks = node.get("marks")
    if isinstance(marks, list):
        node["marks"] = [
            mark
            for mark in marks
            if not (
                isinstance(mark, dict)
                and mark.get("type") == "link"
                and not is_allowed_url((mark.get("attrs") or {}).get("href"), link_protocols)
            )
        ]

    content = node.get("content")
    if isinstance(content, list):
        node["content"] = [
            _sanitize(child, link_protocols, image_protocols, depth + 1) for child in content
        ]

    return node
