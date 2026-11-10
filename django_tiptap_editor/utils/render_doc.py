from __future__ import annotations

from typing import Any

from django.utils.safestring import SafeString, mark_safe

from django_tiptap_editor.constants import (
    DEFAULT_IMAGE_PROTOCOLS,
    DEFAULT_LINK_PROTOCOLS,
    IMAGE_STYLE_PROPERTIES,
)
from django_tiptap_editor.utils.escape_html import escape_html
from django_tiptap_editor.utils.get_css_value import get_css_value
from django_tiptap_editor.utils.get_link_attributes import get_link_attributes
from django_tiptap_editor.utils.sanitize_doc import sanitize_doc

# Simple inline marks: mark type -> wrapping tag. Looked up only for a string
# type: a list or object there is unhashable, and the lookup raised TypeError.
_SIMPLE_MARKS = {
    "bold": "strong",
    "italic": "em",
    "underline": "u",
    "strike": "s",
    "code": "code",
    "subscript": "sub",
    "superscript": "sup",
}

# The alignments Tiptap renders for a table cell. Its HTML parser keeps only
# these three, but a document handed to the editor as JSON keeps whatever value
# it carries and renders text-align only for these, so a stored "justify" (which
# the editor keeps and never shows) renders nothing here too. A tuple, not a
# set: the value is untrusted JSON, and a membership test against a set hashes
# it -- a list or object there raised TypeError, a 500 rather than a skipped
# style -- where a tuple compares it and answers no.
_CELL_ALIGNMENTS = ("left", "center", "right")


def _attrs(item: dict[str, Any]) -> dict[str, Any]:
    """Return a node's or mark's ``attrs``, or ``{}`` when it is not a mapping."""
    attrs = item.get("attrs")
    return attrs if isinstance(attrs, dict) else {}


def _whole_number(value: object) -> int | None:
    """Return ``value`` as an int when the editor reads it as a whole number."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _heading_level(value: object) -> int:
    """Return the level a heading renders at: 1 to 6, else 1."""
    level = _whole_number(value)
    return level if level is not None and 1 <= level <= 6 else 1


def _css_length(value: object) -> str:
    """Return ``value`` if it is a CSS length, else ``""``."""
    token = get_css_value(value)
    return "" if token.replace(".", "", 1).isdigit() else token


# Properties an image's stored ``style`` may carry into the output. The editor
# round-trips that attribute verbatim (the corpus needs ``float`` and ``margin``
# to survive), so this path has to emit it too or JSON storage renders the image
# differently from HTML storage. Shared with the HTML sanitiser's allowlist --
# one vocabulary, so the two paths keep an image's layout identically.
_IMAGE_STYLE_PROPERTIES = frozenset(IMAGE_STYLE_PROPERTIES)

# Sizing carried by the width/height attributes, which the editor writes when an
# image is resized. A style declaration for the same property would outrank the
# attribute, so the attribute wins and the declaration is dropped.
_SIZE_PROPERTIES = ("width", "height")


def _style_declarations(style: object, allowed: frozenset[str]) -> list[tuple[str, str]]:
    """Split a stored ``style`` string into safe (property, value) pairs."""
    if not isinstance(style, str):
        return []
    pairs: list[tuple[str, str]] = []
    for declaration in style.split(";"):
        name, separator, value = declaration.partition(":")
        if not separator:
            continue
        prop = name.strip().lower()
        safe = get_css_value(value)
        if prop in allowed and safe:
            pairs.append((prop, safe))
    return pairs


def _image_style(attrs: dict[str, Any]) -> str:
    """Build an image's ``style``, merging its stored one with its size."""
    stored = _style_declarations(attrs.get("style"), _IMAGE_STYLE_PROPERTIES)
    pairs: list[tuple[str, object]] = [
        (prop, value)
        for prop, value in stored
        if not (prop in _SIZE_PROPERTIES and attrs.get(prop) not in (None, ""))
    ]
    pairs.extend((prop, _css_length(attrs.get(prop))) for prop in _SIZE_PROPERTIES)
    return _style_attr(pairs)


def _style_attr(pairs: list[tuple[str, object]]) -> str:
    """Build a ``style="..."`` attribute from (prop, value) pairs, dropping empties and unsafe values."""
    decls = [f"{prop}: {safe}" for prop, value in pairs if (safe := get_css_value(value))]
    return f' style="{escape_html("; ".join(decls), quote=True)}"' if decls else ""


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
    return f' {name}="{escape_html(str(value), quote=True)}"'


def _wrap_marks(text: str, marks: list[Any]) -> str:
    """Wrap rendered text in its marks (first mark outermost)."""
    out = text
    for mark in reversed(marks):
        if not isinstance(mark, dict):
            continue
        kind = mark.get("type")
        attrs = _attrs(mark)
        if isinstance(kind, str) and kind in _SIMPLE_MARKS:
            tag = _SIMPLE_MARKS[kind]
            out = f"<{tag}>{out}</{tag}>"
        elif kind == "link":
            safe_target, safe_rel = get_link_attributes(attrs.get("target"), attrs.get("rel"))
            href = _attr("href", attrs.get("href"))
            target = _attr("target", safe_target)
            rel = _attr("rel", safe_rel)
            title = _attr("title", attrs.get("title"))
            out = f"<a{href}{target}{rel}{title}>{out}</a>"
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
    return out


def _render_children(node: dict[str, Any]) -> str:
    content = node.get("content")
    if not isinstance(content, list):
        return ""
    return "".join(_render_node(child) for child in content if isinstance(child, dict))


def _cell(tag: str, node: dict[str, Any]) -> str:
    attrs = _attrs(node)
    align = attrs.get("align")
    rendered = (
        _attr("colspan", attrs.get("colspan") if attrs.get("colspan", 1) != 1 else None)
        + _attr("rowspan", attrs.get("rowspan") if attrs.get("rowspan", 1) != 1 else None)
        + _style_attr(
            [
                ("background-color", attrs.get("backgroundColor")),
                ("text-align", align if align in _CELL_ALIGNMENTS else None),
            ]
        )
    )
    return f"<{tag}{rendered}>{_render_children(node)}</{tag}>"


def _render_node(node: dict[str, Any]) -> str:
    kind = node.get("type")
    attrs = _attrs(node)

    if kind == "text":
        text = escape_html(str(node.get("text", "")))
        marks = node.get("marks")
        return _wrap_marks(text, marks) if isinstance(marks, list) else text
    if kind == "paragraph":
        return f"<p{_block_style(attrs)}>{_render_children(node)}</p>"
    if kind == "heading":
        level = _heading_level(attrs.get("level"))
        return f"<h{level}{_block_style(attrs)}>{_render_children(node)}</h{level}>"
    if kind == "bulletList":
        return f"<ul>{_render_children(node)}</ul>"
    if kind == "orderedList":
        # Tiptap writes ``start`` for any value but 1, so a stored ``2.0`` numbers the list from 2 there and has to here.
        start = _whole_number(attrs.get("start"))
        start_attr = _attr("start", start) if start != 1 else ""
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
            + _image_style(attrs)
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
    return _render_children(node)


def render_doc(
    doc: Any,
    *,
    link_protocols: tuple[str, ...] = DEFAULT_LINK_PROTOCOLS,
    image_protocols: tuple[str, ...] = DEFAULT_IMAGE_PROTOCOLS,
) -> SafeString:
    """Render a ProseMirror document (dict) to a safe HTML string."""
    if not isinstance(doc, dict):
        return mark_safe("")
    clean = sanitize_doc(doc, link_protocols=link_protocols, image_protocols=image_protocols)
    return mark_safe(_render_node(clean))
