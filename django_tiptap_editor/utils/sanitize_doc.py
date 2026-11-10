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
    """Return a copy of ``doc`` with disallowed link/image URLs stripped."""
    return _sanitize(doc, link_protocols, image_protocols, 0)


def _is_disallowed_link(mark: object, link_protocols: tuple[str, ...]) -> bool:
    """Return whether ``mark`` is a link whose ``href`` is outside ``link_protocols``."""
    if not isinstance(mark, dict) or mark.get("type") != "link":
        return False
    attrs = mark.get("attrs")
    href = attrs.get("href") if isinstance(attrs, dict) else None
    return not is_allowed_url(href, link_protocols)


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
        node["marks"] = [mark for mark in marks if not _is_disallowed_link(mark, link_protocols)]

    content = node.get("content")
    if isinstance(content, list):
        node["content"] = [
            _sanitize(child, link_protocols, image_protocols, depth + 1) for child in content
        ]

    return node
