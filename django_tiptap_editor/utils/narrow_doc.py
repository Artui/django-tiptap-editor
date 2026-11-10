from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError

from django_tiptap_editor.constants import DOCUMENT_FEATURES, MAX_DOCUMENT_DEPTH
from django_tiptap_editor.utils.resolve_features import resolve_features

# Text blocks: a heading or code block the field lacks becomes a paragraph with
# the same text, as the HTML side turns <h2> and <pre> into <p>. Tuples, not
# sets, as in render_doc: a type is untrusted JSON, and hashing a list or object
# for a set lookup raises TypeError where a tuple compares it and answers no.
_TEXTBLOCK_TYPES = ("heading", "codeBlock")
_INLINE_CONTENT_TYPES = ("paragraph", *_TEXTBLOCK_TYPES)

# The built-in inline nodes. Freed from a node that was unwrapped at block level,
# a run of them is wrapped in a paragraph, because no schema accepts text
# directly inside a document or a list.
_INLINE_TYPES = ("text", "hardBreak", "image")


def narrow_doc(doc: Any, *, config: dict[str, Any] | None) -> Any:
    """Return a copy of ``doc`` holding only what ``config``'s editor can hold."""
    resolved = resolve_features(config or {})
    if resolved is None or not isinstance(doc, dict):
        return doc
    named = frozenset((config or {}).get("extensions") or ())
    return _Narrower(resolved, named).keep(doc, 0)


class _Narrower:
    def __init__(self, features: frozenset[str], extensions: frozenset[str]) -> None:
        self.features = features
        self.extensions = extensions

    def allows(self, kind: object) -> bool:
        if not isinstance(kind, str):
            return False
        return DOCUMENT_FEATURES.get(kind) in self.features or kind in self.extensions

    def attrs(self, item: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        """Return ``item``'s attributes without the ones whose feature is off."""
        attrs = item["attrs"]
        kept: dict[str, Any] = {}
        for name, value in attrs.items():
            feature = DOCUMENT_FEATURES.get(f"{item.get('type')}.{name}")
            if feature is None or feature in self.features:
                kept[name] = value
        return kept, len(kept) != len(attrs)

    def marks(self, marks: list[Any]) -> list[Any]:
        narrowed: list[Any] = []
        for mark in marks:
            if not isinstance(mark, dict) or not self.allows(mark.get("type")):
                continue
            if not isinstance(mark.get("attrs"), dict):
                narrowed.append(mark)
                continue
            attrs, dropped = self.attrs(mark)
            # Each conjunct has a test: without ``dropped`` a bare mark with empty attrs would go ("narrow with their feature" keeps one), and without the value check a textStyle that only coloured its text would stay ("a mark left with no attributes is dropped"), both in tests/utils/test_narrow_doc.py.
            if dropped and not any(value not in (None, "") for value in attrs.values()):
                continue
            narrowed.append({**mark, "attrs": attrs})
        return narrowed

    def keep(self, node: dict[str, Any], depth: int) -> dict[str, Any]:
        """Narrow a node the field keeps: its attributes, marks and content."""
        kept: dict[str, Any] = {**node}
        if isinstance(node.get("attrs"), dict):
            attrs, _dropped = self.attrs(node)
            if attrs:
                kept["attrs"] = attrs
            else:
                del kept["attrs"]
        if isinstance(node.get("marks"), list):
            marks = self.marks(node["marks"])
            if marks:
                kept["marks"] = marks
            else:
                del kept["marks"]
        if isinstance(node.get("content"), list):
            block = node.get("type") not in _INLINE_CONTENT_TYPES
            kept["content"] = self.content(node["content"], block=block, depth=depth + 1)
        return kept

    def content(self, children: list[Any], *, block: bool, depth: int) -> list[Any]:
        # Every level of the walk, kept or freed, comes through here, so this is the one place the recursion is bounded.
        if depth >= MAX_DOCUMENT_DEPTH and any(isinstance(child, dict) for child in children):
            raise ValidationError(
                f"TipTap document nests deeper than the maximum of {MAX_DOCUMENT_DEPTH} nodes."
            )
        narrowed: list[Any] = []
        for child in children:
            if not isinstance(child, dict):
                narrowed.append(child)
            elif self.allows(child.get("type")):
                narrowed.append(self.keep(child, depth))
            else:
                narrowed.extend(self.free(child, block=block, depth=depth))
        return narrowed

    def free(self, node: dict[str, Any], *, block: bool, depth: int) -> list[Any]:
        """Replace a node the field lacks with what it held."""
        children = node.get("content")
        inner = children if isinstance(children, list) else []
        if node.get("type") in _TEXTBLOCK_TYPES:
            paragraph: dict[str, Any] = {"type": "paragraph"}
            text = self.content(inner, block=False, depth=depth + 1)
            if text:
                paragraph["content"] = text
            return [paragraph]
        freed = self.content(inner, block=block, depth=depth + 1)
        if not block:
            return freed
        grouped: list[Any] = []
        run: list[Any] | None = None
        for item in freed:
            if isinstance(item, dict) and item.get("type") in _INLINE_TYPES:
                if run is None:
                    run = []
                    grouped.append({"type": "paragraph", "content": run})
                run.append(item)
            else:
                run = None
                grouped.append(item)
        return grouped
