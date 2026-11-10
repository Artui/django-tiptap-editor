from __future__ import annotations

import re
from html.entities import html5
from html.parser import HTMLParser

from django.core.exceptions import ValidationError
from django.utils.safestring import SafeString, mark_safe

from django_tiptap_editor.constants import MAX_DOCUMENT_DEPTH, PARAGRAPH_BLOCK_TAGS
from django_tiptap_editor.types.html_schema import HtmlSchema
from django_tiptap_editor.utils.escape_html import escape_html
from django_tiptap_editor.utils.get_css_value import get_css_value
from django_tiptap_editor.utils.get_html_schema import get_html_schema
from django_tiptap_editor.utils.get_link_attributes import get_link_attributes
from django_tiptap_editor.utils.is_allowed_url import is_allowed_url

# Elements with no end tag. Listed in full (not just the ones this package
# emits) so a stray ``<input>`` is unwrapped without leaving an open frame on
# the stack that would swallow the rest of the document.
_VOID_TAGS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)

# Elements whose *content* is code rather than text, so unwrapping them would
# paste a script's body into the document as visible prose. Dropped whole.
_DROP_CONTENT_TAGS = frozenset({"script", "style"})

# Attributes carrying a URL, and which protocol allowlist governs each.
_LINK_URL_ATTRIBUTES = frozenset({"href"})
_IMAGE_URL_ATTRIBUTES = frozenset({"src"})

# The built-in vocabulary's block-level tags. Kept, one of these closes a
# paragraph the sanitiser opened rather than landing inside it.
_BLOCK_TAGS = PARAGRAPH_BLOCK_TAGS | {
    "p",
    "ul",
    "ol",
    "hr",
    "table",
    "colgroup",
    "col",
    "tbody",
    "tr",
}

# Blocks whose content is inline text. Converted, one opens its paragraph at
# once, so an empty heading is an empty paragraph, as an empty heading in a
# narrowed JSON document is; kept, one interrupted by a converted block is
# closed there, and what follows it inside becomes paragraphs of its own.
_TEXTBLOCK_TAGS = frozenset({"p", "h1", "h2", "h3", "h4", "h5", "h6", "pre"})

# Elements a browser drops a newline from when it comes first in them.
# ``textarea`` is the third, and it is never kept. No built-in extension emits
# ``listing``; a custom one may declare it, and
# ``test_a_newline_that_becomes_first_in_a_declared_listing_is_kept_visible``
# holds it here.
_LEADING_NEWLINE_TAGS = frozenset({"pre", "listing"})

# HTML's whitespace, which is all a text node between two blocks holds. Narrower
# than str.strip(), which would also take a non-breaking space for nothing.
_HTML_WHITESPACE = " \t\n\r\f"

# A character reference's name, decimal or hex, as html.parser reads one.
_CHARACTER_REFERENCE_NAME = re.compile(r"[0-9]+|[xX][0-9a-fA-F]+")

# What a stack frame is. KEPT is emitted and open; UNWRAPPED was never emitted;
# CONVERTED is a paragraph boundary, emitting nothing itself, inside which text
# gets a paragraph of its own (``paragraph`` says whether one is open); and
# SUSPENDED is a kept inline tag closed at a boundary and reopened by the next
# text inside it. Only the first two exist on an unrestricted field.
_KEPT, _UNWRAPPED, _CONVERTED, _SUSPENDED = range(4)


# The named references a browser reads without their semicolon: HTML's legacy
# names, the entries of its table that do not end in one. None is longer than
# six characters, so the longest one a name can start with is found in at most
# that many lookups however long the name is.
_LEGACY_REFERENCES = frozenset(name for name in html5 if not name.endswith(";"))
_LONGEST_LEGACY_REFERENCE = max(map(len, _LEGACY_REFERENCES))


def _reference(name: str, *, terminated: bool) -> str:
    """Write the named reference ``&name`` the way a browser reads it."""
    if terminated:
        return f"&{escape_html(name)};"
    for end in range(min(len(name), _LONGEST_LEGACY_REFERENCE), 0, -1):
        if name[:end] in _LEGACY_REFERENCES:
            return f"&{name[:end]};{escape_html(name[end:])}"
    return f"&amp;{escape_html(name)}"


class _Frame:
    """One open element: its source tag, what became of it, and its start tag."""

    __slots__ = ("kind", "paragraph", "source", "start")

    def __init__(self, source: str, kind: int, start: str = "") -> None:
        self.source = source
        self.kind = kind
        self.start = start
        # A converted block's open <p> sits inside it: its close closes that <p> first.
        self.paragraph = False

    @property
    def is_inline(self) -> bool:
        return self.kind == _KEPT and self.source not in _BLOCK_TAGS


class _Sanitizer(HTMLParser):
    """Rebuild a document from an allowlist, one token at a time."""

    def __init__(self, schema: HtmlSchema) -> None:
        super().__init__(convert_charrefs=False)
        self.schema = schema
        self.out: list[str] = []
        self.stack: list[_Frame] = []
        # The ``stack`` frames not UNWRAPPED, in the same order; see the module docstring.
        self.chain: list[_Frame] = []
        self.open_tags: dict[str, int] = {}
        self.depth = 0
        self.skipping = 0
        self.entity: str | None = None
        self.newline_at: tuple[int, tuple[int, int]] | None = None
        self.converting = bool(schema.paragraph_blocks)

    def _open(self, start: str, *, void: bool = False) -> None:
        if self.depth >= MAX_DOCUMENT_DEPTH:
            raise ValidationError(
                f"TipTap content nests deeper than the maximum of {MAX_DOCUMENT_DEPTH} elements."
            )
        self.out.append(start)
        if not void:
            self.depth += 1

    def _close(self, frame: _Frame) -> None:
        """Close what ``frame`` holds open: its own tag, or its paragraph."""
        if frame.kind == _KEPT:
            self.out.append(f"</{frame.source}>")
            self.depth -= 1
        elif frame.paragraph:
            self.out.append("</p>")
            self.depth -= 1
            frame.paragraph = False

    def _push(self, frame: _Frame) -> None:
        self.stack.append(frame)
        self.open_tags[frame.source] = self.open_tags.get(frame.source, 0) + 1
        if frame.kind != _UNWRAPPED:
            self.chain.append(frame)

    def _close_from(self, index: int) -> None:
        """Close and drop ``stack[index:]``, innermost first."""
        for frame in reversed(self.stack[index:]):
            self._close(frame)
            self.open_tags[frame.source] -= 1
            if frame.kind != _UNWRAPPED:
                self.chain.pop()
        del self.stack[index:]

    def _break_paragraph(self, *, converted: bool) -> None:
        """Close the paragraph open here, because a block starts at this point."""
        if not self.converting:
            return
        chain = self.chain
        low = len(chain)
        while low and (chain[low - 1].kind == _SUSPENDED or chain[low - 1].is_inline):
            low -= 1
        target: _Frame | None = None
        if low:
            frame = chain[low - 1]
            textblock = frame.kind == _KEPT and frame.source in _TEXTBLOCK_TAGS
            if frame.paragraph or (converted and textblock):
                target = frame
        if target is None and not converted:
            return
        for frame in reversed(chain[low:]):
            self._close(frame)
            frame.kind = _SUSPENDED
        if target is not None:
            self._close(target)
            target.kind = _CONVERTED

    def _ensure_paragraph(self) -> None:
        """Give the text arriving here a paragraph, if it sits in a boundary."""
        if not self.converting:
            return
        chain = self.chain
        low = len(chain)
        while low and chain[low - 1].kind == _SUSPENDED:
            low -= 1
        if low and chain[low - 1].kind == _CONVERTED and not chain[low - 1].paragraph:
            self._open("<p>")
            chain[low - 1].paragraph = True
        for frame in chain[low:]:
            self._open(frame.start)
            frame.kind = _KEPT

    def _attributes(self, tag: str, attrs: list[tuple[str, str | None]]) -> str:
        allowed = self.schema.attributes(tag)
        properties = self.schema.style_properties(tag)
        # Browsers keep the first of a repeated attribute, so only it is checked and written.
        first: dict[str, str | None] = {}
        for raw_name, raw_value in attrs:
            first.setdefault(raw_name.lower(), raw_value)
        if "target" in allowed or "rel" in allowed:
            target, rel = get_link_attributes(first.get("target"), first.get("rel"))
        else:
            target, rel = "", ""
        rendered: list[str] = []
        for name, raw_value in first.items():
            if name == "style":
                declarations = self._style(raw_value, properties)
                if declarations:
                    rendered.append(f' style="{escape_html(declarations, quote=True)}"')
                continue
            if name not in allowed:
                continue
            value = target if name == "target" else rel if name == "rel" else raw_value
            if value is None:
                rendered.append(f" {name}")
                continue
            if not value and name in {"target", "rel"}:
                continue
            if name in _LINK_URL_ATTRIBUTES and not is_allowed_url(
                value, self.schema.link_protocols
            ):
                continue
            if name in _IMAGE_URL_ATTRIBUTES and not is_allowed_url(
                value, self.schema.image_protocols
            ):
                continue
            rendered.append(f' {name}="{escape_html(value, quote=True)}"')
        forced = target == "_blank" and rel and "rel" in allowed
        if forced and not any(part.startswith(' rel="') for part in rendered):
            rendered.append(f' rel="{rel}"')
        return "".join(rendered)

    def _style(self, style: str | None, properties: frozenset[str]) -> str:
        """Keep the allowed declarations of ``style``, verbatim and in order."""
        if not style or not properties:
            return ""
        kept: list[str] = []
        for declaration in style.split(";"):
            name, separator, value = declaration.partition(":")
            if not separator:
                continue
            if name.strip().lower() in properties and get_css_value(value):
                kept.append(declaration.strip())
        if not kept:
            return ""
        trailing = ";" if style.rstrip().endswith(";") else ""
        return "; ".join(kept) + trailing

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in _DROP_CONTENT_TAGS:
            self.skipping += 1
            return
        if tag in self.schema.paragraph_blocks:
            self._break_paragraph(converted=True)
            boundary = _Frame(tag, _CONVERTED)
            self._push(boundary)
            if tag in _TEXTBLOCK_TAGS:
                self._open("<p>")
                boundary.paragraph = True
            return
        if not self.schema.allows(tag):
            if tag not in _VOID_TAGS:
                self._push(_Frame(tag, _UNWRAPPED))
            return
        if tag in _BLOCK_TAGS:
            self._break_paragraph(converted=False)
        else:
            self._ensure_paragraph()
        start = f"<{tag}{self._attributes(tag, attrs)}>"
        self._open(start, void=tag in _VOID_TAGS)
        if tag not in _VOID_TAGS:
            self._push(_Frame(tag, _KEPT, start))
        if tag in _LEADING_NEWLINE_TAGS:
            self.newline_at = (len(self.out), self._source_end(self.get_starttag_text() or ""))

    def _source_end(self, text: str) -> tuple[int, int]:
        """Where in the source ``text``, which starts at ``getpos()``, ends."""
        line, offset = self.getpos()
        newlines = text.count("\n")
        if newlines:
            return line + newlines, len(text) - text.rindex("\n") - 1
        return line, offset + len(text)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _DROP_CONTENT_TAGS and self.skipping:
            self.skipping -= 1
            return
        if tag in _VOID_TAGS:
            return
        if not self.open_tags.get(tag):
            # A stray end tag with nothing open to close.
            return
        index = len(self.stack) - 1
        while self.stack[index].source != tag:
            index -= 1
        self._close_from(index)

    def handle_data(self, data: str) -> None:
        # A dropped element's body is CDATA: all of it arrives as data until it closes.
        if self.skipping:
            return
        if data.strip(_HTML_WHITESPACE):
            self._ensure_paragraph()
        self._first_in_pre(newline=data.startswith(("\n", "\r")))
        self.out.append(escape_html(data))

    def _first_in_pre(self, *, newline: bool) -> None:
        """Keep a newline visible that the sanitiser made first in a ``<pre>``."""
        if self.newline_at is None:
            return
        emitted, source_end = self.newline_at
        self.newline_at = None
        if emitted == len(self.out) and newline and self.getpos() != source_end:
            self.out.append("\n")

    def handle_entityref(self, name: str) -> None:
        self._ensure_paragraph()
        # Whether a reference ended in ';' decides its meaning; ``updatepos`` writes it out.
        self.entity = name

    def updatepos(self, i: int, j: int) -> int:
        if self.entity is not None:
            name, self.entity = self.entity, None
            terminated = self.rawdata[j - 1 : j] == ";"
            # ``&NewLine;`` is the one named newline, and has no legacy form.
            self._first_in_pre(newline=terminated and name == "NewLine")
            self.out.append(_reference(name, terminated=terminated))
        return super().updatepos(i, j)

    def handle_charref(self, name: str) -> None:
        self._ensure_paragraph()
        # Python 3.14+ sends an unfinished ``&#`` at input end here, with the rest as its name.
        if not _CHARACTER_REFERENCE_NAME.fullmatch(name):
            self.out.append(escape_html(f"&#{name}"))
            return
        if name[:1] in "xX":
            newline = name[1:].lstrip("0").lower() == "a"
        else:
            newline = name.lstrip("0") == "10"
        self._first_in_pre(newline=newline)
        self.out.append(f"&#{name};")

    def close(self) -> None:
        # Markup cut off at input end (``<!-- x``): older parsers pass it as text, newer drop it.
        tail = self.rawdata
        if tail.startswith("<") and self.cdata_elem is None:
            self.rawdata = ""
            self.handle_data(tail)
        super().close()

    def result(self) -> str:
        self._close_from(0)
        return "".join(self.out)


def sanitize_html(html: object, *, schema: HtmlSchema | None = None) -> SafeString:
    """Return ``html`` reduced to what the configured editor can emit."""
    if not isinstance(html, str) or not html:
        return mark_safe("")
    parser = _Sanitizer(schema if schema is not None else get_html_schema())
    parser.feed(html)
    parser.close()
    return mark_safe(parser.result())
