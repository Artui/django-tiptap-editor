from __future__ import annotations

import json
import time
from html.parser import HTMLParser
from pathlib import Path

import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.utils.safestring import SafeString

from django_tiptap_editor.constants import EXTENSION_HTML_VOCABULARY, MAX_DOCUMENT_DEPTH
from django_tiptap_editor.types.html_schema import HtmlSchema
from django_tiptap_editor.utils.get_html_schema import get_html_schema
from django_tiptap_editor.utils.render_doc import render_doc
from django_tiptap_editor.utils.sanitize_html import _Sanitizer, sanitize_html

# ---------------------------------------------------------------------------
# Round-trip fidelity.
#
# Every fixture below is output one of this package's two serializers actually
# produces for the shipped default configuration: the editor's getHTML() (dumped
# from the committed bundle) or render_doc's server-side rendering. Sanitising
# any of them must return the same bytes -- a sanitiser that is safe but lossy
# would quietly rewrite an author's document on every save.
#
# The fixtures are not trusted to be complete: the coverage test below derives
# the checklist from EXTENSION_HTML_VOCABULARY -- the same table that builds the
# allowlist and names the built-in extensions -- and fails if any tag, attribute
# or style property an extension can emit is missing here.
# ---------------------------------------------------------------------------

_IMAGE_STYLE = (
    "border: 1px solid rgb(204, 204, 204); border-radius: 4px; display: inline; "
    "float: left; height: 200px; margin: 4px; margin-bottom: 1px; margin-left: 2px; "
    "margin-right: 3px; margin-top: 4px; padding: 5px; padding-bottom: 6px; "
    "padding-left: 7px; padding-right: 8px; padding-top: 9px; vertical-align: middle; "
    "width: 300px;"
)

SERIALIZED: dict[str, str] = {
    "paragraph": (
        '<p style="margin: 10px; margin-block-end: 4px; padding-left: 30px; '
        'text-align: center;">aligned</p>'
    ),
    "inline marks": (
        "<p><strong>b</strong><em>i</em><u>u</u><s>s</s><code>c</code>"
        "<sub>sub</sub><sup>sup</sup></p>"
    ),
    "text style": (
        '<p><span style="font-family: Arial, sans-serif; color: rgb(255, 0, 0); '
        'background-color: rgb(0, 255, 0); font-size: 18px;">styled</span></p>'
    ),
    "link": (
        '<p><a class="cta" href="https://example.test/x?a=1&amp;b=2" target="_blank" '
        'rel="noopener noreferrer">link</a></p>'
    ),
    "image": (
        '<p><img src="https://example.test/i.png" alt="alt" title="t" width="300" '
        f'height="200" style="{_IMAGE_STYLE}"></p>'
    ),
    "lists": '<ul><li><p>a</p></li></ul><ol start="3" type="a"><li><p>b</p></li></ol>',
    "blocks": "<blockquote><p>q</p></blockquote><hr><p>a<br>b</p>",
    "code block": '<pre><code class="language-python">x = 1</code></pre>',
    "table sized by min-width": (
        '<table style="min-width: 50px;"><colgroup><col style="min-width: 25px;">'
        '</colgroup><tbody><tr><th colspan="2" rowspan="1" colwidth="120" '
        'style="background-color: #eeeeee">h</th></tr><tr>'
        '<td colspan="1" rowspan="2" style="background-color: #ffffff"><p>c</p></td>'
        "</tr></tbody></table>"
    ),
    "table sized by width": (
        '<table style="width: 120px;"><colgroup><col style="width: 120px;"></colgroup>'
        '<tbody><tr><td colspan="1" rowspan="1" colwidth="120"><p>a</p></td></tr></tbody></table>'
    ),
    "text and character references": "<p>a &amp; b &lt;c&gt; \"d\" 'e' &nbsp; caf&eacute; &#233;</p>",
    "empty paragraph": "<p></p><p>x</p>",
}
SERIALIZED.update(
    {
        f"heading {level}": (
            f'<h{level} style="margin: 1px; margin-block-end: 2px; padding-left: 3px; '
            f'text-align: right;">h{level}</h{level}>'
        )
        for level in range(1, 7)
    }
)

# What the editor itself renders for the attributes Tiptap 3 began emitting: a
# link title and table-cell alignment. js/test/editor-render-fixture.test.ts
# generates the file and fails while it is stale, so these are loaded rather
# than pasted and cannot drift from the editor that produced them.
EDITOR_RENDER = json.loads(
    (Path(__file__).parent / "fixtures" / "editor_render.json").read_text(encoding="utf-8")
)
SERIALIZED.update({f"editor: {case['name']}": case["html"] for case in EDITOR_RENDER["cases"]})


class _Vocabulary(HTMLParser):
    """Collect the (tag, attribute) and (tag, style property) pairs in a fixture."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.tags: set[str] = set()
        self.attributes: set[tuple[str, str]] = set()
        self.styles: set[tuple[str, str]] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.add(tag)
        for name, value in attrs:
            if name == "style":
                for declaration in (value or "").split(";"):
                    prop, separator, _ = declaration.partition(":")
                    if separator:
                        self.styles.add((tag, prop.strip()))
            else:
                self.attributes.add((tag, name))


def _observed() -> _Vocabulary:
    parser = _Vocabulary()
    for html in SERIALIZED.values():
        parser.feed(html)
    return parser


def _declared() -> tuple[set[str], set[tuple[str, str]], set[tuple[str, str]]]:
    tags: set[str] = set()
    attributes: set[tuple[str, str]] = set()
    styles: set[tuple[str, str]] = set()
    for vocabulary in EXTENSION_HTML_VOCABULARY.values():
        for tag, entry in vocabulary.items():
            tags.add(tag)
            attributes.update((tag, name) for name in entry.get("attrs", ()))
            styles.update((tag, prop) for prop in entry.get("styles", ()))
    return tags, attributes, styles


def test_fixtures_cover_every_tag_the_extensions_can_emit() -> None:
    tags, _attributes, _styles = _declared()
    assert _observed().tags == tags


def test_fixtures_cover_every_attribute_the_extensions_can_emit() -> None:
    _tags, attributes, _styles = _declared()
    assert attributes - _observed().attributes == set()


def test_fixtures_cover_every_style_property_the_extensions_can_emit() -> None:
    _tags, _attributes, styles = _declared()
    assert styles - _observed().styles == set()


@pytest.mark.parametrize("name", sorted(SERIALIZED))
def test_serialized_output_survives_byte_identically(name: str) -> None:
    assert str(sanitize_html(SERIALIZED[name])) == SERIALIZED[name]


# The full node and mark vocabulary of the JSON path, so the server-side
# renderer's output can be checked against the sanitiser's allowlist directly.
FULL_DOC: dict = {
    "type": "doc",
    "content": [
        {
            "type": "paragraph",
            "attrs": {
                "margin": "10px",
                "marginBlockEnd": "4px",
                "paddingLeft": "30px",
                "textAlign": "center",
            },
            "content": [
                {"type": "text", "text": "plain "},
                *(
                    {"type": "text", "text": mark, "marks": [{"type": mark}]}
                    for mark in (
                        "bold",
                        "italic",
                        "underline",
                        "strike",
                        "code",
                        "subscript",
                        "superscript",
                    )
                ),
                {
                    "type": "text",
                    "text": "styled",
                    "marks": [
                        {
                            "type": "textStyle",
                            "attrs": {
                                "color": "rgb(255, 0, 0)",
                                "backgroundColor": "rgb(0, 255, 0)",
                                "fontFamily": "Arial, sans-serif",
                                "fontSize": "18px",
                            },
                        }
                    ],
                },
                {
                    "type": "text",
                    "text": "link",
                    "marks": [
                        {
                            "type": "link",
                            "attrs": {
                                "href": "https://example.test/?a=1&b=2",
                                "target": "_blank",
                                "rel": "nofollow",
                                "title": "t",
                            },
                        }
                    ],
                },
                {"type": "hardBreak"},
                {
                    "type": "image",
                    "attrs": {
                        "src": "https://example.test/i.png",
                        "alt": "alt",
                        "title": "t",
                        "width": "300",
                        "height": "200",
                        "style": "float: left; margin: 4px",
                    },
                },
            ],
        },
        *(
            {
                "type": "heading",
                "attrs": {"level": level, "textAlign": "right"},
                "content": [{"type": "text", "text": f"h{level}"}],
            }
            for level in range(1, 7)
        ),
        {
            "type": "bulletList",
            "content": [{"type": "listItem", "content": [{"type": "paragraph"}]}],
        },
        {
            "type": "orderedList",
            "attrs": {"start": 3},
            "content": [{"type": "listItem", "content": [{"type": "paragraph"}]}],
        },
        {"type": "blockquote", "content": [{"type": "paragraph"}]},
        {"type": "codeBlock", "content": [{"type": "text", "text": "x = 1"}]},
        {"type": "horizontalRule"},
        {
            "type": "table",
            "content": [
                {
                    "type": "tableRow",
                    "content": [
                        {
                            "type": "tableHeader",
                            "attrs": {
                                "colspan": 2,
                                "backgroundColor": "#eeeeee",
                                "align": "center",
                            },
                            "content": [{"type": "paragraph"}],
                        },
                        {
                            "type": "tableCell",
                            "attrs": {"rowspan": 2, "align": "right"},
                            "content": [{"type": "paragraph"}],
                        },
                    ],
                }
            ],
        },
    ],
}

# Tags only the browser-side serializer emits: the column group comes from the
# editor's table view, and the Python renderer writes a plain <table><tbody>.
_EDITOR_ONLY_TAGS = frozenset({"col", "colgroup"})


def test_renderer_output_is_a_fixed_point_of_the_sanitizer() -> None:
    rendered = str(render_doc(FULL_DOC))
    assert str(sanitize_html(rendered)) == rendered


def test_renderer_output_exercises_the_whole_allowlist() -> None:
    parser = _Vocabulary()
    parser.feed(str(render_doc(FULL_DOC)))
    tags, _attributes, _styles = _declared()
    assert tags - parser.tags == _EDITOR_ONLY_TAGS


# ---------------------------------------------------------------------------
# What the allowlist refuses.
# ---------------------------------------------------------------------------


def test_event_handler_attribute_is_dropped() -> None:
    assert str(sanitize_html("<img src=x onerror=alert(document.cookie)>")) == '<img src="x">'


def test_script_element_and_its_body_are_dropped() -> None:
    assert str(sanitize_html("<p>a<script>alert(1)</script>b</p>")) == "<p>ab</p>"


def test_style_element_and_its_body_are_dropped() -> None:
    assert str(sanitize_html("<style>body{display:none}</style>x")) == "x"


def test_unknown_tag_is_unwrapped_keeping_its_text() -> None:
    assert str(sanitize_html('<div onclick="x()">keep me</div>')) == "keep me"


def test_javascript_href_is_dropped() -> None:
    assert str(sanitize_html('<a href="javascript:alert(1)">x</a>')) == "<a>x</a>"


def test_obfuscated_scheme_is_dropped() -> None:
    assert str(sanitize_html('<a href="java\tscript:alert(1)">x</a>')) == "<a>x</a>"


def test_relative_href_is_kept() -> None:
    assert str(sanitize_html('<a href="/local">x</a>')) == '<a href="/local">x</a>'


def test_reverse_tabnabbing_rel_is_replaced() -> None:
    assert str(sanitize_html('<a href="https://e.test" target="_blank" rel="opener">x</a>')) == (
        '<a href="https://e.test" target="_blank" rel="noopener noreferrer">x</a>'
    )


def test_blank_target_gains_a_rel_when_the_document_omits_it() -> None:
    assert str(sanitize_html('<a href="https://e.test" target="_blank">x</a>')) == (
        '<a href="https://e.test" target="_blank" rel="noopener noreferrer">x</a>'
    )


def test_unknown_target_is_dropped() -> None:
    assert str(sanitize_html('<a href="/x" target="evilframe">x</a>')) == '<a href="/x">x</a>'


def test_style_property_outside_the_allowlist_is_dropped() -> None:
    assert str(sanitize_html('<p style="position: fixed; text-align: left">x</p>')) == (
        '<p style="text-align: left">x</p>'
    )


def test_style_value_carrying_a_url_is_dropped() -> None:
    assert str(sanitize_html('<p style="margin: url(javascript:alert(1))">x</p>')) == "<p>x</p>"


def test_image_src_protocol_is_allowlisted() -> None:
    assert str(sanitize_html('<img src="vbscript:x">')) == "<img>"


def test_unbalanced_markup_is_closed() -> None:
    assert str(sanitize_html("<p><em>a<strong>b</p>")) == "<p><em>a<strong>b</strong></em></p>"


def test_stray_end_tag_is_ignored() -> None:
    assert str(sanitize_html("</p>stray")) == "stray"


def test_comment_is_dropped() -> None:
    assert str(sanitize_html("<p>a<!-- note -->b</p>")) == "<p>ab</p>"


# From Python 3.14, html.parser hands a character reference left unfinished at
# the end of the input to handle_charref with everything after "&#" as its
# name, markup included; earlier versions pass it to handle_data as text. On
# 3.14 a decimal reference running into a hex letter is unfinished wherever it
# sits. With no semicolon later in the input, every version gives these.
_UNFINISHED_CHARACTER_REFERENCES = {
    "digits-then-a-hex-letter": (
        "<p>&#1a<img src=x onerror=alert(1)></p>",
        "<p>&amp;#1a&lt;img src=x onerror=alert(1)&gt;&lt;/p&gt;</p>",
    ),
    "an-uppercase-hex-letter": (
        '<p>&#9F<a href="javascript:x">y</a></p>',
        '<p>&amp;#9F&lt;a href="javascript:x"&gt;y&lt;/a&gt;&lt;/p&gt;</p>',
    ),
    "after-a-finished-paragraph": (
        "<p>a</p><p>&#12e<b onclick=x>y</b></p>",
        "<p>a</p><p>&amp;#12e&lt;b onclick=x&gt;y&lt;/b&gt;&lt;/p&gt;</p>",
    ),
    "at-the-end-of-the-input": ("<p>x &#1a", "<p>x &amp;#1a</p>"),
}


@pytest.mark.parametrize(
    ("html", "expected"),
    _UNFINISHED_CHARACTER_REFERENCES.values(),
    ids=_UNFINISHED_CHARACTER_REFERENCES.keys(),
)
def test_an_unfinished_character_reference_is_written_as_text(html: str, expected: str) -> None:
    assert str(sanitize_html(html)) == expected


class _CharacterReferences(HTMLParser):
    """The names this interpreter's html.parser reports as character references."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.names: list[str] = []

    def handle_charref(self, name: str) -> None:
        self.names.append(name)


def _reports_the_rest_as_a_reference() -> bool:
    """Whether html.parser hands ``&#1a`` the rest of the input as its name."""
    parser = _CharacterReferences()
    parser.feed("&#1a<b>;")
    parser.close()
    return parser.names == ["1a<b>;"]


# With a semicolon later in the input, Python 3.10 to 3.13 pass "&#" along as
# text and parse what follows as markup, which is filtered as usual; a parser
# that hands the rest over as the reference's name gets it written as text.
# Keyed on what the parser does, not on its version number.
def test_an_unfinished_character_reference_before_a_semicolon_lets_no_markup_through() -> None:
    cleaned = str(sanitize_html("<p>&#1a<strong onclick=x>x</strong>;</p>"))
    if _reports_the_rest_as_a_reference():
        assert cleaned == "<p>&amp;#1a&lt;strong onclick=x&gt;x&lt;/strong&gt;;&lt;/p&gt;</p>"
    else:
        assert cleaned == "<p>&amp;#1a<strong>x</strong>;</p>"


# The same rule at the handler, which no interpreter before 3.14 reaches
# through the parser: a name that is not a reference's is written as text.
@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("1a<b onclick=x>", "&amp;#1a&lt;b onclick=x&gt;"),
        ("1a", "&amp;#1a"),
        ("x", "&amp;#x"),
        ("", "&amp;#"),
        ("12 ", "&amp;#12 "),
        ("10", "&#10;"),
        ("X0a", "&#X0a;"),
    ],
)
def test_the_character_reference_handler_writes_any_other_name_as_text(
    name: str, expected: str
) -> None:
    sanitizer = _Sanitizer(get_html_schema())
    sanitizer.handle_charref(name)
    assert sanitizer.result() == expected


# html.parser only ever hands handle_entityref a name of letters and digits,
# on every version; markup in one must still come out as text.
def test_the_named_reference_handler_cannot_write_markup() -> None:
    sanitizer = _Sanitizer(get_html_schema())
    sanitizer.handle_entityref("a<b onclick=x>")
    assert sanitizer.result() == "&a&lt;b onclick=x&gt;;"


def test_valueless_attribute_is_kept_bare() -> None:
    assert str(sanitize_html("<ol start><li></li></ol>")) == "<ol start><li></li></ol>"


def test_non_string_and_empty_input_render_empty() -> None:
    assert sanitize_html(None) == ""
    assert sanitize_html("") == ""
    assert isinstance(sanitize_html(None), SafeString)


def test_deeply_nested_markup_is_refused() -> None:
    with pytest.raises(ValidationError, match="nests deeper"):
        sanitize_html("<blockquote>" * (MAX_DOCUMENT_DEPTH + 1))


def test_nesting_up_to_the_limit_is_accepted() -> None:
    deep = "<blockquote>" * MAX_DOCUMENT_DEPTH
    assert str(sanitize_html(deep)) == deep + "</blockquote>" * MAX_DOCUMENT_DEPTH


def test_an_explicit_schema_overrides_the_project_one() -> None:
    schema = HtmlSchema(tags={"p": frozenset()}, styles={})
    assert str(sanitize_html("<p><strong>x</strong></p>", schema=schema)) == "<p>x</p>"


@override_settings(TIPTAP_DEFAULT_CONFIG={"linkProtocols": ["https"]})
def test_configured_link_protocols_narrow_the_allowlist() -> None:
    assert (
        str(sanitize_html('<a href="http://e.test">x</a>', schema=get_html_schema())) == "<a>x</a>"
    )


@override_settings(
    TIPTAP_EXTRA_EXTENSIONS={"callout": {"aside": {"attrs": ["class"], "styles": ["color"]}}}
)
def test_a_declared_custom_extension_survives() -> None:
    markup = '<aside class="warn" style="color: red">careful</aside>'
    assert str(sanitize_html(markup, schema=get_html_schema())) == markup


@override_settings(TIPTAP_EXTRA_EXTENSIONS=["callout"])
def test_an_undeclared_custom_extension_warns_by_name() -> None:
    with pytest.warns(UserWarning, match="'callout' does not declare the HTML it emits"):
        schema = get_html_schema()
    assert str(sanitize_html("<aside>careful</aside>", schema=schema)) == "careful"


def test_a_style_attribute_on_a_tag_with_no_style_vocabulary_is_dropped() -> None:
    assert str(sanitize_html('<a href="/x" style="color: red">y</a>')) == '<a href="/x">y</a>'


def test_a_declaration_without_a_colon_is_dropped() -> None:
    assert str(sanitize_html('<p style="text-align: left; oops">x</p>')) == (
        '<p style="text-align: left">x</p>'
    )


def test_an_end_tag_for_a_void_element_is_ignored() -> None:
    assert str(sanitize_html("<p>a<br></br>b</p>")) == "<p>a<br>b</p>"


def test_an_unknown_void_element_leaves_nothing_open() -> None:
    assert str(sanitize_html("<p>a<input>b</p>")) == "<p>ab</p>"


def test_unclosed_unknown_and_known_tags_both_end_cleanly() -> None:
    assert str(sanitize_html("<div><p>x")) == "<p>x</p>"


# Inputs a client can post to a restricted field, each built to make a walk over
# the open elements pay for every unknown tag before it (which emits nothing, so
# no depth limit stops them piling up) or for every boundary already passed. On
# a sanitiser whose walks step over those, each of these takes many seconds at
# this size; done in linear time, each takes a fraction of one. The bound is far
# above the linear figure, so a slow runner does not fail it, and far below the
# quadratic one. Closing tags are a cost of their own, on every field, and have
# their own test below.
_N = 40_000
_SLOW_INPUTS = {
    "text-in-unknown-tags": ("<div>x" * _N, ["bold"]),
    "entities-after-unknown-tags": ("<div>" * _N + "&amp;" * _N, ["bold"]),
    "charrefs-after-unknown-tags": ("<div>" * _N + "&#169;" * _N, ["bold"]),
    "kept-inline-after-unknown-tags": ("<div>" * _N + "<br>" * _N, ["bold"]),
    "kept-block-after-unknown-tags": ("<div>" * _N + "<hr>" * _N, ["horizontalRule"]),
    "converted-items-in-unknown-tags": ("<div><li>x" * _N, ["bold"]),
    "converted-headings": ("<h2>x" * _N, ["bold"]),
}


@pytest.mark.parametrize(("html", "features"), _SLOW_INPUTS.values(), ids=_SLOW_INPUTS.keys())
def test_a_restricted_field_cleans_in_linear_time(html: str, features: list[str]) -> None:
    schema = get_html_schema({"features": features})
    start = time.perf_counter()
    sanitize_html(html, schema=schema)
    assert time.perf_counter() - start < 2.5


# Inputs that make each end tag pay for every element open below it: unknown tags
# pile up with no depth limit to stop them, and an end tag that matched nothing
# (a stray), or matched the innermost element (scanned from the outermost), used
# to walk all of them. Each takes tens of seconds at this size where every end
# tag walks the stack, and a fraction of one where it does not. Both kinds of
# field, because matching an end tag is the same code on each.
_CLOSING_INPUTS = {
    "stray-end-tags-after-unknown-tags": "<div>" * _N + "</b>" * _N,
    "matched-end-tags-after-unknown-tags": "<div>" * _N + "</div>" * _N,
    "kept-marks-after-unknown-tags": "<div>" * _N + "<strong>x</strong>" * _N,
    "stray-end-tags-between-unknown-tags": "<div></b>" * _N,
}


@pytest.mark.parametrize("features", [None, ["bold"]], ids=["unrestricted", "restricted"])
@pytest.mark.parametrize("html", _CLOSING_INPUTS.values(), ids=_CLOSING_INPUTS.keys())
def test_closing_tags_clean_in_linear_time(html: str, features: list[str] | None) -> None:
    schema = get_html_schema({"features": features} if features is not None else None)
    start = time.perf_counter()
    sanitize_html(html, schema=schema)
    assert time.perf_counter() - start < 2.5
