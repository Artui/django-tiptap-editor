from __future__ import annotations

from html.parser import HTMLParser

import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.utils.safestring import SafeString

from django_tiptap_editor.constants import EXTENSION_HTML_VOCABULARY, MAX_DOCUMENT_DEPTH
from django_tiptap_editor.types.html_schema import HtmlSchema
from django_tiptap_editor.utils.get_html_schema import get_html_schema
from django_tiptap_editor.utils.render_doc import render_doc
from django_tiptap_editor.utils.sanitize_html import sanitize_html

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
                            "attrs": {"colspan": 2, "backgroundColor": "#eeeeee"},
                            "content": [{"type": "paragraph"}],
                        },
                        {
                            "type": "tableCell",
                            "attrs": {"rowspan": 2},
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
