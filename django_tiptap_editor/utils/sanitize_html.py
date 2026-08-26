"""Allowlist sanitiser for HTML-stored TipTap content, in pure Python.

HTML storage means the editor writes ``editor.getHTML()`` into a textarea and a
normal POST submits it. ProseMirror's schema drops everything it cannot model --
but it runs in the *browser*, so it is a formatter, not a security boundary: a
client that skips the editor and posts the field directly stores whatever it
likes, and the docs then tell a project to render that. This walks the submitted
markup and keeps only what the configured extensions can emit
(``get_html_schema``): every other tag is unwrapped, every other attribute
dropped, link and image URLs are protocol-allowlisted, and inline styles pass
the same conservative CSS gate the JSON renderer uses.

Unwrapping rather than deleting is deliberate: a tag the allowlist does not know
loses its wrapper, never its text, so no sanitiser pass can quietly empty half a
document. What the editor itself produces round-trips byte-identically.
"""

from __future__ import annotations

from html.parser import HTMLParser

from django.core.exceptions import ValidationError
from django.utils.safestring import SafeString, mark_safe

from django_tiptap_editor.constants import MAX_DOCUMENT_DEPTH
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


class _Sanitizer(HTMLParser):
    """Rebuild a document from an allowlist, one token at a time.

    ``convert_charrefs=False`` so character references are re-emitted exactly as
    written: with conversion on, ``&nbsp;`` would come back as a literal
    non-breaking space and every save would rewrite the author's markup.
    """

    def __init__(self, schema: HtmlSchema) -> None:
        super().__init__(convert_charrefs=False)
        self.schema = schema
        self.out: list[str] = []
        # (source tag, emitted tag or None when the tag was unwrapped).
        self.stack: list[tuple[str, str | None]] = []
        self.depth = 0
        self.skipping = 0

    def _attributes(self, tag: str, attrs: list[tuple[str, str | None]]) -> str:
        allowed = self.schema.attributes(tag)
        properties = self.schema.style_properties(tag)
        if "target" in allowed or "rel" in allowed:
            values = {name.lower(): value for name, value in attrs}
            target, rel = get_link_attributes(values.get("target"), values.get("rel"))
        else:
            target, rel = "", ""
        rendered: list[str] = []
        for raw_name, raw_value in attrs:
            name = raw_name.lower()
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
        """Keep the allowed declarations of ``style``, verbatim and in order.

        Each surviving declaration is re-emitted as written rather than
        reformatted, so a value the editor spelled one way and the renderer
        another both come back unchanged.
        """
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
        if not self.schema.allows(tag):
            if tag not in _VOID_TAGS:
                self.stack.append((tag, None))
            return
        if self.depth >= MAX_DOCUMENT_DEPTH:
            raise ValidationError(
                f"TipTap content nests deeper than the maximum of {MAX_DOCUMENT_DEPTH} elements."
            )
        self.out.append(f"<{tag}{self._attributes(tag, attrs)}>")
        if tag not in _VOID_TAGS:
            self.stack.append((tag, tag))
            self.depth += 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _DROP_CONTENT_TAGS and self.skipping:
            self.skipping -= 1
            return
        if tag in _VOID_TAGS:
            return
        opened = [index for index, (source, _e) in enumerate(self.stack) if source == tag]
        if not opened:
            # A stray end tag with nothing open to close.
            return
        # Close everything opened inside the innermost match too, so crossed
        # tags come back nested rather than leaving the output malformed.
        for _source, emitted in reversed(self.stack[opened[-1] :]):
            if emitted is not None:
                self.out.append(f"</{emitted}>")
                self.depth -= 1
        del self.stack[opened[-1] :]

    def handle_data(self, data: str) -> None:
        # The only guard the skip needs: a dropped element's body is CDATA to
        # the parser, so everything inside it arrives here as data and no start
        # tag, end tag or character reference is reported until it closes.
        if not self.skipping:
            self.out.append(escape_html(data))

    def handle_entityref(self, name: str) -> None:
        self.out.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.out.append(f"&#{name};")

    def result(self) -> str:
        for _source, emitted in reversed(self.stack):
            if emitted is not None:
                self.out.append(f"</{emitted}>")
        self.stack.clear()
        return "".join(self.out)


def sanitize_html(html: object, *, schema: HtmlSchema | None = None) -> SafeString:
    """Return ``html`` reduced to what the configured editor can emit.

    Unknown tags are unwrapped (their text survives), unknown attributes are
    dropped, ``script`` / ``style`` content is discarded, link and image URLs are
    protocol-allowlisted, and inline styles keep only allowed properties with
    safe values. Non-string input renders as an empty string.

    Raises ``ValidationError`` for content nested deeper than
    ``MAX_DOCUMENT_DEPTH``. The result is marked safe, which is the whole point:
    after this, the stored value is trustworthy to render.
    """
    if not isinstance(html, str) or not html:
        return mark_safe("")
    parser = _Sanitizer(schema if schema is not None else get_html_schema())
    parser.feed(html)
    parser.close()
    return mark_safe(parser.result())
