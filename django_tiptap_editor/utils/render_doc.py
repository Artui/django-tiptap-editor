"""Pure-Python ProseMirror-JSON → HTML renderer for the package's schema.

Renders a stored document to HTML **server-side, with no Node and no editor** —
the zero-JS display path for JSON storage (especially programmatically-authored
documents that have no editor-produced mirror). It covers exactly the package's
node/mark set; unknown nodes/marks degrade to their text content rather than
raising, so it never loses content silently.

Safety: the document is protocol-allowlisted first (``sanitize_doc`` strips
disallowed link/image URLs), text and attribute values are HTML-escaped, and
inline ``style`` values are passed through a conservative CSS allowlist — so the
output is safe to mark for ``|safe`` even for untrusted JSON. It is faithful to,
but not byte-identical with, the JS ``getHTML()`` output.
"""

from __future__ import annotations

import re
from typing import Any

from django.utils.html import escape
from django.utils.safestring import SafeString, mark_safe

from django_tiptap_editor.constants import DEFAULT_IMAGE_PROTOCOLS, DEFAULT_LINK_PROTOCOLS
from django_tiptap_editor.utils.sanitize_doc import sanitize_doc

# Simple inline marks: mark type -> wrapping tag.
_SIMPLE_MARKS = {
    "bold": "strong",
    "italic": "em",
    "underline": "u",
    "strike": "s",
    "code": "code",
    "subscript": "sub",
    "superscript": "sup",
}

# Conservative CSS value allowlist: word chars, spaces, and the punctuation real
# values use (#hex, %, commas, dots, parens for rgb(), hyphens). Rejects anything
# with ``;`` ``:`` ``{`` ``}`` ``<`` ``>`` quotes — i.e. property-injection,
# url(...:...) and markup — so style attributes can't smuggle script.
_CSS_VALUE_RE = re.compile(r"^[#%(),.\-\s\w]+$")


def _css_value(value: object) -> str:
    """Return a CSS value if it is a safe simple token, else ``""``."""
    if not isinstance(value, str):
        return ""
    token = value.strip()
    if not token or not _CSS_VALUE_RE.match(token) or "expression" in token.lower():
        return ""
    return token


def _style_attr(pairs: list[tuple[str, object]]) -> str:
    """Build a ``style="..."`` attribute from (prop, value) pairs, dropping
    empties and unsafe values. Returns ``""`` when nothing survives."""
    decls = [f"{prop}: {safe}" for prop, value in pairs if (safe := _css_value(value))]
    return f' style="{escape("; ".join(decls))}"' if decls else ""


def _block_style(attrs: dict[str, Any]) -> str:
    return _style_attr(
        [
            ("margin", attrs.get("margin")),
            ("margin-block-end", attrs.get("marginBlockEnd")),
            ("padding-left", attrs.get("paddingLeft")),
            ("text-align", attrs.get("textAlign")),
        ]
    )


def _attr(name: str, value: object) -> str:
    """Render a single HTML attribute, or ``""`` for null/empty values."""
    if value is None or value == "":
        return ""
    return f' {name}="{escape(str(value))}"'


def _wrap_marks(text: str, marks: list[Any]) -> str:
    """Wrap rendered text in its marks (first mark outermost)."""
    out = text
    for mark in reversed(marks):
        if not isinstance(mark, dict):
            continue
        kind = mark.get("type")
        attrs = mark.get("attrs") or {}
        if kind in _SIMPLE_MARKS:
            tag = _SIMPLE_MARKS[kind]
            out = f"<{tag}>{out}</{tag}>"
        elif kind == "link":
            href = _attr("href", attrs.get("href"))
            target = _attr("target", attrs.get("target"))
            rel = _attr("rel", attrs.get("rel"))
            out = f"<a{href}{target}{rel}>{out}</a>"
        elif kind == "textStyle":
            style = _style_attr(
                [
                    ("color", attrs.get("color")),
                    ("background-color", attrs.get("backgroundColor")),
                    ("font-family", attrs.get("fontFamily")),
                    ("font-size", attrs.get("fontSize")),
                ]
            )
            if style:
                out = f"<span{style}>{out}</span>"
        # Unknown marks: leave the text unwrapped.
    return out


def _render_children(node: dict[str, Any]) -> str:
    content = node.get("content")
    if not isinstance(content, list):
        return ""
    return "".join(_render_node(child) for child in content if isinstance(child, dict))


def _cell(tag: str, node: dict[str, Any]) -> str:
    attrs = node.get("attrs") or {}
    rendered = (
        _attr("colspan", attrs.get("colspan") if attrs.get("colspan", 1) != 1 else None)
        + _attr("rowspan", attrs.get("rowspan") if attrs.get("rowspan", 1) != 1 else None)
        + _style_attr([("background-color", attrs.get("backgroundColor"))])
    )
    return f"<{tag}{rendered}>{_render_children(node)}</{tag}>"


def _render_node(node: dict[str, Any]) -> str:
    kind = node.get("type")
    attrs = node.get("attrs") or {}

    if kind == "text":
        text = escape(str(node.get("text", "")))
        marks = node.get("marks")
        return _wrap_marks(text, marks) if isinstance(marks, list) else text
    if kind == "paragraph":
        return f"<p{_block_style(attrs)}>{_render_children(node)}</p>"
    if kind == "heading":
        level = attrs.get("level", 1)
        level = level if level in {1, 2, 3, 4, 5, 6} else 1
        return f"<h{level}{_block_style(attrs)}>{_render_children(node)}</h{level}>"
    if kind == "bulletList":
        return f"<ul>{_render_children(node)}</ul>"
    if kind == "orderedList":
        start = attrs.get("start")
        start_attr = _attr("start", start) if isinstance(start, int) and start != 1 else ""
        return f"<ol{start_attr}>{_render_children(node)}</ol>"
    if kind == "listItem":
        return f"<li>{_render_children(node)}</li>"
    if kind == "blockquote":
        return f"<blockquote>{_render_children(node)}</blockquote>"
    if kind == "codeBlock":
        return f"<pre><code>{_render_children(node)}</code></pre>"
    if kind == "horizontalRule":
        return "<hr>"
    if kind == "hardBreak":
        return "<br>"
    if kind == "image":
        rendered = (
            _attr("src", attrs.get("src"))
            + _attr("alt", attrs.get("alt"))
            + _attr("title", attrs.get("title"))
            + _attr("width", attrs.get("width"))
            + _attr("height", attrs.get("height"))
            + _style_attr([("width", attrs.get("width")), ("height", attrs.get("height"))])
        )
        return f"<img{rendered}>"
    if kind == "table":
        return f"<table><tbody>{_render_children(node)}</tbody></table>"
    if kind == "tableRow":
        return f"<tr>{_render_children(node)}</tr>"
    if kind == "tableHeader":
        return _cell("th", node)
    if kind == "tableCell":
        return _cell("td", node)
    if kind == "doc":
        return _render_children(node)
    # Unknown node: keep its content, drop the wrapper.
    return _render_children(node)


def render_doc(
    doc: Any,
    *,
    link_protocols: tuple[str, ...] = DEFAULT_LINK_PROTOCOLS,
    image_protocols: tuple[str, ...] = DEFAULT_IMAGE_PROTOCOLS,
) -> SafeString:
    """Render a ProseMirror document (dict) to a safe HTML string.

    The document is protocol-allowlisted first; the result is HTML-escaped and
    CSS-validated, so it is safe to render with ``|safe``. Non-dict / empty input
    renders as an empty string.
    """
    if not isinstance(doc, dict):
        return mark_safe("")
    clean = sanitize_doc(doc, link_protocols=link_protocols, image_protocols=image_protocols)
    return mark_safe(_render_node(clean))
