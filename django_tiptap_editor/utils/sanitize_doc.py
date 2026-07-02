"""Pure-Python protocol allowlisting for a stored ProseMirror document.

JSON storage means a document can be written by something other than the editor
(an API, an import, a hand-edit). ProseMirror's schema only allowlists protocols
on *parse*, which a stored-JSON path never runs — so a doc could carry a
``javascript:`` link ``href`` or image ``src``. This walks the document tree and
strips any URL whose scheme is outside the allowlist (relative / anchor URLs,
which have no scheme, are always kept), before the value is persisted.

This is deliberately narrow: it secures the URL-bearing attributes, not the full
schema. Full structural validation is the editor's job (and a future Python
renderer's); see the JSON-storage design notes.
"""

from __future__ import annotations

import re
from typing import Any

from django_tiptap_editor.constants import DEFAULT_IMAGE_PROTOCOLS, DEFAULT_LINK_PROTOCOLS

_SCHEME_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):")

# ASCII whitespace and C0/DEL control characters (``\x00``–``\x20`` and ``\x7f``).
# A browser strips these while resolving a URL — tabs/newlines are removed from
# anywhere in the string, leading controls/spaces are trimmed — so an attacker
# embeds them mid-scheme (``java\nscript:``) to hide a disallowed scheme from a
# naive parser. We remove them before scheme detection to see what the browser
# will.
_URL_STRIP_RE = re.compile(r"[\x00-\x20\x7f]")


def _scheme(url: object) -> str:
    """Return the lowercased URL scheme, or ``""`` for a relative/anchor URL.

    Whitespace and control characters are stripped first (see ``_URL_STRIP_RE``),
    mirroring the browser, so ``java\\nscript:`` resolves to the ``javascript``
    scheme here just as it would on click.
    """
    if not isinstance(url, str):
        return ""
    match = _SCHEME_RE.match(_URL_STRIP_RE.sub("", url))
    return match.group(1).lower() if match else ""


def _allowed(url: object, protocols: tuple[str, ...]) -> bool:
    scheme = _scheme(url)
    return scheme == "" or scheme in protocols


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
    """
    if not isinstance(doc, dict):
        return doc

    node: dict[str, Any] = {**doc}

    if node.get("type") == "image":
        attrs = node.get("attrs")
        if isinstance(attrs, dict) and not _allowed(attrs.get("src"), image_protocols):
            node["attrs"] = {**attrs, "src": ""}

    marks = node.get("marks")
    if isinstance(marks, list):
        node["marks"] = [
            mark
            for mark in marks
            if not (
                isinstance(mark, dict)
                and mark.get("type") == "link"
                and not _allowed((mark.get("attrs") or {}).get("href"), link_protocols)
            )
        ]

    content = node.get("content")
    if isinstance(content, list):
        node["content"] = [
            sanitize_doc(child, link_protocols=link_protocols, image_protocols=image_protocols)
            for child in content
        ]

    return node
