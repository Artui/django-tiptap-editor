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

A field restricted with ``features`` adds one rule. A built-in block its editor
cannot hold (``HtmlSchema.paragraph_blocks``: a heading, a list item, a cell, a
quotation, a code block) is not unwrapped but turned into a paragraph boundary,
as the editor does with such markup pasted into it: unwrapped, two headings
would come back as one line of text. Paragraphs are opened lazily, where text
arrives, so editor output that already nests a ``<p>`` in a list item or a cell
comes back as flat paragraphs rather than one paragraph inside another.

Every step of that is linear in the input. Unknown tags do not count toward
``MAX_DOCUMENT_DEPTH`` (they emit nothing), so a client can open as many as it
likes, and a walk over the open elements that passed each of them would make
every later text node pay for all of them. So the walks that place paragraphs
read a second list beside the stack, ``chain``, holding only the elements that
are not unwrapped, and a converted block's paragraph is a flag on that block
rather than an element of its own, so nothing is ever inserted into or removed
from the middle of either list. What a walk passes over on the chain is kept
inline tags, which count toward the depth limit, and inline tags a boundary
suspended, which the next text reopens (and so count toward it again), so no
walk is longer than that limit.

An end tag does walk the stack, unknown tags included, so that walk is paid for
differently: a count of open frames per tag says at once whether anything
matches, and the walk runs down from the top and closes every frame it passes,
so each frame is passed once however many end tags arrive.
"""

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
    """Write the named reference ``&name`` the way a browser reads it.

    With its semicolon a reference is kept as written. Without one, a browser
    reads the longest legacy name it starts with and the rest as text, so
    ``&ltimg`` is ``<img``, or reads it all as text when it starts with none, so
    ``&bar`` is ``&bar``. Writing a semicolon after the whole name, as this used
    to, gave ``&ltimg;``, which a browser shows as ``<img;``, and turned
    ``&hellip`` (shown as typed) into an ellipsis. The result always ends its
    reference, so text that follows cannot run into it.

    html.parser passes a name of letters, digits, hyphens and dots, the rest of
    the input included when Python 3.14 reaches its end mid-reference, so the
    escapes change nothing today. They are there so a parser that ever passes
    more cannot write markup: ``test_a_named_reference_cannot_write_markup``.
    """
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
        # A converted block's open <p>, which sits directly inside it: closing
        # the block closes the paragraph, and the paragraph closes first.
        self.paragraph = False

    @property
    def is_inline(self) -> bool:
        return self.kind == _KEPT and self.source not in _BLOCK_TAGS


class _Sanitizer(HTMLParser):
    """Rebuild a document from an allowlist, one token at a time.

    ``convert_charrefs=False`` so character references are re-emitted as
    written: with conversion on, ``&nbsp;`` would come back as a literal
    non-breaking space and every save would rewrite the author's markup. The one
    rewrite is a named reference missing its semicolon, which is written the way
    a browser reads it (``_reference``).
    """

    def __init__(self, schema: HtmlSchema) -> None:
        super().__init__(convert_charrefs=False)
        self.schema = schema
        self.out: list[str] = []
        self.stack: list[_Frame] = []
        # The frames of ``stack`` that are not UNWRAPPED, in the same order; see
        # the module docstring. A frame never changes between unwrapped and
        # anything else, so it is in this list for exactly as long as it is on
        # the stack, and the two are only ever appended to or cut at the top.
        self.chain: list[_Frame] = []
        # How many frames of each source tag are on the stack, so an end tag
        # that matches nothing is known to without a walk. Without it every
        # stray ``</b>`` walked the whole stack, which unknown tags can make as
        # deep as a client likes: ``"<div>" * 40000 + "</b>" * 40000`` took half
        # a minute. ``test_closing_tags_clean_in_linear_time`` holds it, and
        # ``test_an_end_tag_for_an_element_already_closed_is_ignored`` holds the
        # count going down as frames close: left up, a second ``</strong>``
        # would search for a frame that is gone and fail.
        self.open_tags: dict[str, int] = {}
        self.depth = 0
        self.skipping = 0
        # A named reference reported but not yet written; see ``updatepos``.
        self.entity: str | None = None
        # For a <pre> just opened: how much output there was after its start
        # tag, and where that tag ended in the source; see ``handle_data``.
        self.newline_at: tuple[int, tuple[int, int]] | None = None
        # Converted, paragraph and suspended frames are only ever made for a tag
        # in ``paragraph_blocks``, so with none of those both paragraph walks
        # below are no-ops, and they return before walking. Without this, text
        # inside N unwrapped tags walks all N on an unrestricted field, which
        # made ``"<div>x" * 20000`` take seconds where it took milliseconds; the
        # output is the same either way, so no test can hold it but the clock.
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
        """Close the paragraph open here, because a block starts at this point.

        Walks down past unwrapped and suspended frames and kept inline tags to
        the first frame that is anything else. Each rule is held by a case of
        ``test_a_block_the_field_lacks_becomes_a_paragraph`` in
        tests/forms/test_fields.py. A paragraph the sanitiser opened is closed for
        any block, which keeps ``<li>a<p>b</p></li>`` flat
        ("kept-block-in-converted"). A kept text block (a ``<p>`` the client
        sent) is closed only for a converted block, and becomes a boundary itself
        so that its remaining text is a paragraph of its own
        ("block-in-paragraph"); for a kept block it is left as it always was,
        which ``test_a_kept_block_in_a_kept_paragraph_is_left_as_it_was_on_a_restricted_field``
        holds. Kept inline tags above are closed with it and reopened by the next
        text ("mark-across-boundary").
        """
        if not self.converting:
            return
        chain = self.chain
        # Skipping a suspended frame changes no output a mutation run could find:
        # the next text reopens suspended frames, and a block opened before then
        # stops this walk above them. It is skipped because it stands for a
        # closed inline tag, which is what the walk passes over.
        low = len(chain)
        while low and (chain[low - 1].kind == _SUSPENDED or chain[low - 1].is_inline):
            low -= 1
        target: _Frame | None = None
        if low:
            frame = chain[low - 1]
            # The kind test changes no output either: the only other frame with
            # a text block's name is a converted one, and taking that as target
            # closes nothing its own paragraph flag would not already have. It
            # says what the rule is about, a <p> or heading the client sent.
            textblock = frame.kind == _KEPT and frame.source in _TEXTBLOCK_TAGS
            if frame.paragraph or (converted and textblock):
                target = frame
        if target is None and not converted:
            return
        # Above ``low`` is only what the walk passed: kept inline tags, which
        # close and suspend, and suspended ones, which hold nothing open, so
        # closing and suspending them again changes nothing.
        for frame in reversed(chain[low:]):
            self._close(frame)
            frame.kind = _SUSPENDED
        if target is not None:
            # A converted block's paragraph closes, leaving the block a boundary
            # with none open; a kept text block closes and becomes that boundary.
            self._close(target)
            target.kind = _CONVERTED

    def _ensure_paragraph(self) -> None:
        """Give the text arriving here a paragraph, if it sits in a boundary.

        Text directly inside a converted block (or a kept text block a boundary
        closed) opens a ``<p>``; inline tags suspended at a boundary reopen
        inside it, or where the text is, so a mark split by a converted block
        resumes after it. Anywhere else this changes nothing.
        """
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
        # A browser reads an attribute written twice from its first occurrence
        # and ignores the rest, so only the first is checked and written. Kept
        # whole, ``<a href="/a" href="/b">`` came back with both, and target and
        # rel were computed from the last occurrence where a browser reads the
        # first. ``test_a_duplicated_attribute_keeps_its_first_occurrence``.
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
        # Close everything opened inside the innermost match too, so crossed
        # tags come back nested rather than leaving the output malformed. The
        # search runs down from the top, and every frame it passes is closed
        # with the match, so no frame is ever passed twice: a forward scan from
        # the bottom made ``"<div>" * 40000 + "</div>" * 40000`` walk the whole
        # stack once per end tag.
        index = len(self.stack) - 1
        while self.stack[index].source != tag:
            index -= 1
        self._close_from(index)

    def handle_data(self, data: str) -> None:
        # The only guard the skip needs: a dropped element's body is CDATA to
        # the parser, so everything inside it arrives here as data and no start
        # tag, end tag or character reference is reported until it closes.
        if self.skipping:
            return
        # Whitespace between blocks opens no paragraph: it would be an empty one.
        if data.strip(_HTML_WHITESPACE):
            self._ensure_paragraph()
        # CR LF and a lone CR count: a browser reads both as one newline.
        self._first_in_pre(newline=data.startswith(("\n", "\r")))
        self.out.append(escape_html(data))

    def _first_in_pre(self, *, newline: bool) -> None:
        """Keep a newline visible that the sanitiser made first in a ``<pre>``.

        Called before text is written. A browser drops a newline that comes
        first in a ``<pre>``. Where it comes first only because the markup
        before it was not kept, it was not first in the source and the browser
        kept it there, so one is written ahead of it to be dropped instead. Each
        condition is held by a case of
        ``test_a_newline_that_becomes_first_in_a_pre_is_kept_visible``:
        "after-a-kept-tag" (nothing emitted since), "not-first" (the newline)
        and "directly-after-the-start-tag" (where it sat).
        """
        if self.newline_at is None:
            return
        emitted, source_end = self.newline_at
        self.newline_at = None
        if emitted == len(self.out) and newline and self.getpos() != source_end:
            self.out.append("\n")

    def handle_entityref(self, name: str) -> None:
        self._ensure_paragraph()
        # Whether the reference ended in a semicolon is not passed in, and it
        # decides what the reference means, so it is written out by
        # ``updatepos``, which the parser calls next with the reference's end.
        self.entity = name

    def updatepos(self, i: int, j: int) -> int:
        if self.entity is not None:
            name, self.entity = self.entity, None
            terminated = self.rawdata[j - 1 : j] == ";"
            # ``&NewLine;`` is the one named newline, and has no legacy form.
            # Cases of ``test_a_newline_that_becomes_first_in_a_pre_is_kept_visible``
            # hold each half: "an-unterminated-named-reference" the semicolon,
            # "another-named-reference" the name.
            self._first_in_pre(newline=terminated and name == "NewLine")
            self.out.append(_reference(name, terminated=terminated))
        return super().updatepos(i, j)

    def handle_charref(self, name: str) -> None:
        self._ensure_paragraph()
        # From Python 3.14, a character reference left unfinished at the end of
        # the input reaches here with everything after ``&#`` as its name, the
        # rest of the document included, where earlier versions pass it to
        # ``handle_data`` as text. ``&#1a`` is unfinished wherever it sits: the
        # parser holds the rest back as possibly more of the reference, then
        # hands all of it over on close. Writing that name as a reference would
        # pass the markup after it through unsanitised, so a name that is not a
        # reference's is written as the text it is. A browser would read ``&#1``
        # and parse the markup after it; text is the safe reading of what the
        # parser no longer separates, not the browser's.
        # ``test_an_unfinished_character_reference_is_written_as_text`` holds
        # it on 3.14, and ``test_the_character_reference_handler_writes_any_other_name_as_text``
        # on every version.
        if not _CHARACTER_REFERENCE_NAME.fullmatch(name):
            self.out.append(escape_html(f"&#{name}"))
            return
        # A newline written as ``&#10;`` or ``&#xA;``, leading zeros allowed.
        # Compared as text: ``int`` refuses a number of a few thousand digits.
        # "a-hex-reference" and "a-hex-reference-to-another-character" hold the
        # hex test and "an-uppercase-hex-reference" its capital X;
        # "a-reference-after-an-unknown-tag" and "a-carriage-return-reference"
        # the decimal one, and "a-reference-with-leading-zeros" its zeros.
        if name[:1] in "xX":
            newline = name[1:].lstrip("0").lower() == "a"
        else:
            newline = name.lstrip("0") == "10"
        self._first_in_pre(newline=newline)
        self.out.append(f"&#{name};")

    def close(self) -> None:
        # Markup the input ends inside of (``<!-- x``, ``<![CDATA[ x``,
        # ``<strong``, ``<a href="x``, ``</p``) is still unparsed here, and what
        # the parser's own close does with it depends on its patch release:
        # older ones pass it to ``handle_data`` as text, newer ones drop a tag
        # and report a comment or a CDATA section, none of which is kept. So it
        # is written as text here, on every version, and taken from the parser
        # so it is not handed over a second time
        # (``test_markup_left_unfinished_at_the_end_is_written_once``). A
        # browser drops most of these, and reads the start of an unfinished
        # CDATA section as markup; text is the reading that loses nothing the
        # author typed and runs nothing they did not, not the browser's.
        # ``test_markup_left_unfinished_at_the_end_is_written_as_text`` holds it.
        #
        # Only markup is taken: a tail that does not start with "<" is a
        # reference the parser finishes itself, and it is read as the parser
        # reports it (``test_a_reference_that_ends_the_input_is_read_as_the_parser_reports_it``
        # holds that on 3.14, and
        # ``test_an_unfinished_character_reference_before_a_semicolon_lets_no_markup_through``
        # on 3.10 and 3.13). Nor is the content of a raw-text element such
        # as <script> or <textarea>, which the parser reads as text already: an
        # end tag left unfinished there would be written escaped into a kept
        # <xmp>, whose content is not unescaped, and escaped again by a second
        # pass (``test_an_end_tag_left_unfinished_in_a_raw_text_element_is_left_to_the_parser``).
        tail = self.rawdata
        if tail.startswith("<") and self.cdata_elem is None:
            self.rawdata = ""
            self.handle_data(tail)
        super().close()

    def result(self) -> str:
        self._close_from(0)
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
