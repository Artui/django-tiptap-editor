from __future__ import annotations

import warnings
from html.parser import HTMLParser
from typing import Any

import pytest
from django import forms
from django.core.exceptions import ValidationError
from django.template import Context, Template
from django.test import override_settings

from django_tiptap_editor.constants import MAX_DOCUMENT_DEPTH
from django_tiptap_editor.forms.fields import TipTapFormField
from django_tiptap_editor.utils.resolve_features import resolve_features
from django_tiptap_editor.widgets.tiptap_widget import TipTapWidget

PAYLOAD = "<img src=x onerror=alert(document.cookie)>"


class ArticleForm(forms.Form):
    body = TipTapFormField()


def test_default_widget_is_tiptap() -> None:
    assert isinstance(TipTapFormField().widget, TipTapWidget)


def _restricted(features: list[str] | None, **config: Any) -> TipTapFormField:
    return TipTapFormField(
        required=False, widget=TipTapWidget(config={"features": features, **config})
    )


def test_features_narrow_what_a_direct_post_can_store() -> None:
    # docs/configuration.md, docs/security.md and the CHANGELOG say a field
    # restricted with ``features`` is sanitised against those features: a client
    # that skips the editor cannot store a heading or a table the editor of that
    # field could not have made. The text stays, one paragraph per former block.
    class EmailForm(forms.Form):
        body = TipTapFormField(widget=TipTapWidget(config={"features": ["bold"]}))

    posted = "<h2>Title</h2><table><tbody><tr><td><p>cell</p></td></tr></tbody></table>"
    form = EmailForm(data={"body": posted})
    assert form.is_valid()
    assert form.cleaned_data["body"] == "<p>Title</p><p>cell</p>"


@pytest.mark.parametrize(
    ("posted", "expected"),
    [
        # Unwrapping these, as an unknown tag is, would run the blocks together.
        pytest.param("<h2>A</h2><h2>B</h2>", "<p>A</p><p>B</p>", id="headings"),
        pytest.param("<ul><li>a</li><li>b</li></ul>", "<p>a</p><p>b</p>", id="tight-list"),
        pytest.param("<ul><li><p>a</p></li><li><p>b</p></li></ul>", "<p>a</p><p>b</p>", id="list"),
        pytest.param("<blockquote><p>a</p><p>b</p></blockquote>", "<p>a</p><p>b</p>", id="quote"),
        pytest.param("<pre><code>x = 1</code></pre>", "<p>x = 1</p>", id="code-block"),
        # A heading with nothing in it is still a block, as an empty heading
        # converted in a JSON document is an empty paragraph.
        pytest.param("<h2></h2><p>a</p>", "<p></p><p>a</p>", id="empty-heading"),
        # A container is only unwrapped: what it held decides the paragraphs.
        pytest.param(
            "<table><tbody><tr><td><p>a</p></td><td><p>b</p></td></tr></tbody></table>",
            "<p>a</p><p>b</p>",
            id="table",
        ),
        # A paragraph opened for loose text closes when a kept block starts.
        pytest.param("<li>a<p>b</p></li>", "<p>a</p><p>b</p>", id="kept-block-in-converted"),
        # A converted block inside a paragraph splits it; the paragraph resumes.
        pytest.param("<p>x<h2>y</h2>z</p>", "<p>x</p><p>y</p><p>z</p>", id="block-in-paragraph"),
        # A mark open across the boundary is closed before it and reopened after.
        pytest.param(
            "<p><strong>x<h2>y</h2>z</strong></p>",
            "<p><strong>x</strong></p><p>y</p><p><strong>z</strong></p>",
            id="mark-across-boundary",
        ),
        # A genuinely unknown tag is unwrapped exactly as it always was.
        pytest.param("<div>a</div><div>b</div>", "ab", id="unknown-tag"),
        # The cases below each hold one step of the walk that a mutation run
        # found no other test holding.
        # A kept paragraph a boundary split is itself a boundary, so the text
        # after the heading opens a paragraph of its own rather than one nested
        # inside the converted list item's.
        pytest.param(
            "<ul><li><p>x<h2>y</h2>z</p></li></ul>",
            "<p>x</p><p>y</p><p>z</p>",
            id="split-paragraph-in-converted",
        ),
        # Text inside an unknown tag still finds the converted block below it.
        pytest.param("<ul><li><font>a</font></li></ul>", "<p>a</p>", id="unknown-in-converted"),
        # Whitespace between blocks opens no paragraph, so none comes back empty.
        pytest.param("<ul>\n<li>\n<p>a</p>\n</li>\n</ul>", "\n\n<p>a</p>\n\n", id="pretty-printed"),
        # A kept mark opening a converted block's text opens its paragraph.
        pytest.param(
            "<ul><li><strong>a</strong></li></ul>", "<p><strong>a</strong></p>", id="mark-first"
        ),
        # So do a character reference and an entity.
        pytest.param(
            "<ul><li>&amp;</li><li>&#169;</li></ul>", "<p>&amp;</p><p>&#169;</p>", id="references"
        ),
        # A paragraph still open when the input ends is closed.
        pytest.param("<ul><li>a", "<p>a</p>", id="unclosed"),
        # Closing an unknown tag inside a boundary leaves the boundary open, so
        # the heading after it still closes the quote's paragraph first.
        pytest.param(
            "<blockquote><div>a</div><h2>b</h2>c</blockquote>",
            "<p>a</p><p>b</p><p>c</p>",
            id="unknown-tag-closed-in-boundary",
        ),
    ],
)
def test_a_block_the_field_lacks_becomes_a_paragraph(posted: str, expected: str) -> None:
    assert _restricted(["bold"]).clean(posted) == expected


@pytest.mark.parametrize(
    ("features", "posted", "expected"),
    [
        # Each case holds one member of a tag table in sanitize_html or
        # constants, which a mutation run found no other test holding.
        # Cells are boundaries of their own (PARAGRAPH_BLOCK_TAGS).
        pytest.param([], "<td>a</td><td>b</td>", "<p>a</p><p>b</p>", id="cells"),
        pytest.param([], "<th>a</th><th>b</th>", "<p>a</p><p>b</p>", id="header-cells"),
        # A kept block closes the paragraph a converted quote opened before it
        # (_BLOCK_TAGS), and the text after it opens another.
        pytest.param(
            ["bulletList"],
            "<blockquote>a<ul><li>b</li></ul>c</blockquote>",
            "<p>a</p><ul><li>b</li></ul><p>c</p>",
            id="kept-ul",
        ),
        pytest.param(
            ["orderedList"],
            "<blockquote>a<ol><li>b</li></ol>c</blockquote>",
            "<p>a</p><ol><li>b</li></ol><p>c</p>",
            id="kept-ol",
        ),
        pytest.param(
            ["horizontalRule"],
            "<blockquote>a<hr>b</blockquote>",
            "<p>a</p><hr><p>b</p>",
            id="kept-hr",
        ),
        pytest.param(
            ["table"],
            "<blockquote>a<table><tbody><tr><td>b</td></tr></tbody></table>c</blockquote>",
            "<p>a</p><table><tbody><tr><td>b</td></tr></tbody></table><p>c</p>",
            id="kept-table",
        ),
        pytest.param(
            ["table"],
            "<blockquote>a<tbody>b</tbody>c</blockquote>",
            "<p>a</p><tbody>b</tbody><p>c</p>",
            id="kept-tbody",
        ),
        pytest.param(
            ["table"],
            "<blockquote>a<tr>b</tr>c</blockquote>",
            "<p>a</p><tr>b</tr><p>c</p>",
            id="kept-tr",
        ),
        pytest.param(
            ["table"],
            "<blockquote>a<colgroup></colgroup>b</blockquote>",
            "<p>a</p><colgroup></colgroup><p>b</p>",
            id="kept-colgroup",
        ),
        pytest.param(
            ["table"], "<blockquote>a<col>b</blockquote>", "<p>a</p><col><p>b</p>", id="kept-col"
        ),
        # An empty text block is an empty paragraph, as narrowing an empty
        # heading or code block in a JSON document gives (_TEXTBLOCK_TAGS).
        *(
            pytest.param([], f"<{tag}></{tag}>", "<p></p>", id=f"empty-{tag}")
            for tag in ("h1", "h2", "h3", "h4", "h5", "h6", "pre")
        ),
        # A non-breaking space is text, not the whitespace between two blocks.
        pytest.param([], "<li>\xa0</li>", "<p>\xa0</p>", id="nbsp"),
    ],
)
def test_each_block_tag_takes_its_part_in_conversion(
    features: list[str], posted: str, expected: str
) -> None:
    assert _restricted(features).clean(posted) == expected


def test_a_kept_block_is_kept_inside_a_converted_one() -> None:
    # Lists on, headings off: the heading inside the list item becomes its
    # paragraph, and the list itself survives untouched.
    field = _restricted(["bulletList"])
    assert field.clean("<ul><li><h3>a</h3></li></ul>") == "<ul><li><p>a</p></li></ul>"


def test_a_mark_is_closed_before_a_paragraph_inside_a_kept_block() -> None:
    # Bold straight inside a kept quote has no paragraph to close, but the
    # converted heading's paragraph still may not open inside the <strong>.
    field = _restricted(["blockquote", "bold"])
    assert field.clean("<blockquote><strong>x<h2>y</h2>z</strong></blockquote>") == (
        "<blockquote><strong>x</strong><p>y</p><strong>z</strong></blockquote>"
    )


def test_attributes_and_styles_narrow_with_their_feature() -> None:
    posted = (
        '<p style="text-align: center">a <span style="color: red; font-size: 18px">b</span></p>'
    )
    assert _restricted(["fontSize", "textAlign"]).clean(posted) == (
        '<p style="text-align: center">a <span style="font-size: 18px">b</span></p>'
    )
    assert _restricted(["color"]).clean(posted) == ('<p>a <span style="color: red">b</span></p>')


def test_a_feature_that_only_decorates_admits_no_tag_of_its_own() -> None:
    # textAlign writes text-align on headings, so its vocabulary names h1-h6. A
    # field with alignment and no headings must still not keep a heading.
    posted = '<h2 style="text-align: center">x</h2><p style="text-align: center">y</p>'
    assert _restricted(["textAlign"]).clean(posted) == (
        '<p>x</p><p style="text-align: center">y</p>'
    )


@override_settings(TIPTAP_DEFAULT_CONFIG={"features": ["bold"]})
def test_a_project_wide_feature_list_narrows_every_field() -> None:
    assert TipTapFormField().clean("<h2>a</h2><p><em>b</em></p>") == "<p>a</p><p>b</p>"


@override_settings(TIPTAP_DEFAULT_CONFIG={"features": ["bold"]})
def test_features_none_on_one_field_lifts_the_project_wide_list() -> None:
    assert _restricted(None).clean("<h2>a</h2>") == "<h2>a</h2>"


@override_settings(TIPTAP_DEFAULT_CONFIG={"features": ["bold"]})
def test_a_field_without_the_tiptap_widget_uses_the_global_allowlist() -> None:
    # Nothing to read a per-field config from, so the project's whole allowlist
    # applies rather than a guess at what the editor would have mounted.
    field = TipTapFormField(widget=forms.Textarea)
    assert field.clean("<h2>a</h2><script>x</script>") == "<h2>a</h2>"


@override_settings(TIPTAP_EXTRA_EXTENSIONS={"callout": {"aside": {}}, "badge": {"mark": {}}})
def test_a_restricted_field_keeps_only_the_custom_extensions_it_names() -> None:
    posted = "<aside>a</aside><mark>b</mark>"
    assert _restricted(["bold"], extensions=["callout"]).clean(posted) == "<aside>a</aside>b"
    # Unrestricted, every declared extension is in the allowlist, as before.
    assert _restricted(None, extensions=["callout"]).clean(posted) == posted


@override_settings(TIPTAP_EXTRA_EXTENSIONS={"headings": {"h2": {}}})
def test_a_named_extension_admits_its_tags_even_one_a_feature_also_owns() -> None:
    # docs/extending.md says so: an extension's vocabulary is admitted as it is
    # declared, so a field without heading that names one keeps <h2>.
    posted = "<h2>a</h2>"
    assert _restricted([], extensions=["headings"]).clean(posted) == posted
    assert _restricted([]).clean(posted) == "<p>a</p>"


@override_settings(TIPTAP_EXTRA_EXTENSIONS=["legacy"])
def test_a_restricted_field_warns_only_for_an_undeclared_extension_it_names() -> None:
    with warnings.catch_warnings():
        # "legacy" declares no vocabulary, but this field does not name it, so it
        # is not part of this field's allowlist and there is nothing to warn about.
        warnings.simplefilter("error")
        _restricted(["bold"]).clean("<p>a</p>")
    with pytest.warns(UserWarning, match="'legacy'"):
        _restricted(["bold"], extensions=["legacy"]).clean("<p>a</p>")


def test_a_direct_post_cannot_store_an_event_handler() -> None:
    # The reproduction: the widget is a plain textarea, so a client that never
    # loads the editor posts the field directly and the browser-side schema
    # never runs.
    form = ArticleForm(data={"body": PAYLOAD})
    assert form.is_valid()
    assert form.cleaned_data["body"] == '<img src="x">'
    assert "onerror" not in Template("{{ body }}").render(Context(form.cleaned_data))


def test_editor_output_survives_cleaning_unchanged() -> None:
    markup = '<p style="text-align: center;">hello <strong>world</strong></p>'
    form = ArticleForm(data={"body": markup})
    assert form.is_valid()
    assert form.cleaned_data["body"] == markup


def test_cleaned_value_is_a_plain_string() -> None:
    # It is assigned to a CharField / TextField column, and reads back from the
    # database as a str; handing back a SafeString here would make "just
    # cleaned" and "loaded again" render differently.
    form = ArticleForm(data={"body": "<p>x</p>"})
    assert form.is_valid()
    assert type(form.cleaned_data["body"]) is str


def test_content_that_sanitizes_to_nothing_fails_a_required_field() -> None:
    form = ArticleForm(data={"body": "<script>alert(1)</script>"})
    assert not form.is_valid()
    assert form.errors["body"] == ["This field is required."]


def test_length_validation_counts_the_sanitized_value() -> None:
    field = TipTapFormField(max_length=10)
    assert field.clean('<div class="wrapper">short</div>') == "short"


def test_deeply_nested_markup_is_a_field_error() -> None:
    with pytest.raises(ValidationError, match="nests deeper"):
        TipTapFormField().clean("<blockquote>" * (MAX_DOCUMENT_DEPTH + 1))


# The battery the per-field rule is held to: real editor shapes plus the
# hostile ones a direct POST can send, on configs that each exclude something
# different. Every input is checked for three properties rather than one
# expected string, because the point is that no combination breaks any of them:
# the output is a fixed point, no paragraph nests in another, and the text
# survives in order with each former block still a block of its own.
_BATTERY = [
    "<h2>A</h2><h2>B</h2><p>c</p>",
    "<ul><li><p>a</p><ul><li><p>b</p></li></ul></li><li><p>c</p></li></ul>",
    "<ol><li>a</li><li>b<ol><li>c</li></ol></li></ol>",
    "<table><tbody><tr><th><p>h</p></th><td><p>c1</p><p>c2</p></td></tr></tbody></table>",
    "<ul><li><blockquote><p>q</p><h3>r</h3></blockquote></li></ul>",
    "<h2><strong>a</strong> b</h2><p><strong>c</strong></p>",
    "<p><em>x<h2>y</h2>z</em></p>",
    "<p>x<h2>y</h2>z</p>",
    "<strong>x<h2>y</h2>z</strong>",
    "<li>a<p>b</p>c</li>",
    "<td>a<blockquote>b</blockquote></td>",
    "<pre><code>a</code></pre><h1>b</h1>",
    "<h2>a<h3>b</h3>c</h2>",
    "<blockquote>a<ul><li>b</li></ul>c</blockquote>",
]
_CONFIGS = [[], ["bold", "italic"], ["bulletList", "orderedList"], ["heading"], ["blockquote"]]

# The block tags each feature owns, restated by hand so the battery's "nothing
# the field lacks survives" check does not lean on the code it is checking.
_BLOCK_FEATURES = {
    "heading": {"h1", "h2", "h3", "h4", "h5", "h6"},
    "blockquote": {"blockquote"},
    "codeBlock": {"pre"},
    "bulletList": {"ul"},
    "orderedList": {"ol"},
    "listItem": {"li"},
    "table": {"table", "tbody", "colgroup", "col"},
    "tableRow": {"tr"},
    "tableCell": {"td"},
    "tableHeader": {"th"},
}

# Tags that start or end a block, for the text-order check below.
_BLOCKS = frozenset(
    {"p", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "ul", "ol", "li"}
    | {"table", "tbody", "tr", "td", "th"}
)


class _Shape(HTMLParser):
    """Read the visible text of each block, and the deepest paragraph nesting."""

    def __init__(self) -> None:
        super().__init__()
        self.blocks: list[str] = [""]
        self.tags: set[str] = set()
        self.paragraphs = 0
        self.deepest = 0

    def _boundary(self) -> None:
        if self.blocks[-1].strip():
            self.blocks.append("")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.add(tag)
        if tag in _BLOCKS:
            self._boundary()
        if tag == "p":
            self.paragraphs += 1
            self.deepest = max(self.deepest, self.paragraphs)

    def handle_endtag(self, tag: str) -> None:
        if tag in _BLOCKS:
            self._boundary()
        if tag == "p":
            self.paragraphs -= 1

    def handle_data(self, data: str) -> None:
        self.blocks[-1] += data


def _shape(html: str) -> _Shape:
    parser = _Shape()
    parser.feed(html)
    parser.close()
    return parser


def _texts(html: str) -> list[str]:
    return [block.strip() for block in _shape(html).blocks if block.strip()]


@pytest.mark.parametrize("features", _CONFIGS, ids=lambda f: "+".join(f) or "core")
@pytest.mark.parametrize("posted", _BATTERY)
def test_narrowing_keeps_blocks_apart_flat_and_stable(features: list[str], posted: str) -> None:
    field = _restricted(features)
    cleaned = field.clean(posted)
    resolved = resolve_features({"features": features})
    assert resolved is not None
    lacking = {
        tag for feature, tags in _BLOCK_FEATURES.items() if feature not in resolved for tag in tags
    }
    assert not _shape(cleaned).tags & lacking
    assert field.clean(cleaned) == cleaned
    assert _shape(cleaned).deepest <= 1
    assert _texts(cleaned) == _texts(posted)


def test_an_unrestricted_field_leaves_nested_paragraphs_as_they_were() -> None:
    # The flattening is part of converting a block the field lacks. Applied to
    # every field it would rewrite markup that has always been stored as posted.
    assert TipTapFormField().clean("<p>a<p>b</p></p>") == "<p>a<p>b</p></p>"


def test_a_kept_block_in_a_kept_paragraph_is_left_as_it_was_on_a_restricted_field() -> None:
    # Only a block the field lacks is a boundary. A list the field keeps, inside
    # a paragraph and a mark it keeps, stays where it was posted, as it does on
    # an unrestricted field; closing the mark or the paragraph around it would
    # be the flattening applied to markup nothing converted.
    posted = "<p><strong>a<ul><li>b</li></ul>c</strong></p>"
    assert _restricted(["bold", "bulletList"]).clean(posted) == posted


def test_a_mark_opened_just_before_a_converted_block_is_left_empty() -> None:
    # docs/security.md documents the empty pair: the mark is closed at the
    # boundary as it is when it holds text, and reopened after it.
    posted = "<strong><h2>b</h2>c</strong>"
    assert _restricted(["bold"]).clean(posted) == "<strong></strong><p>b</p><strong>c</strong>"


def test_only_the_paragraphs_the_sanitiser_opens_are_kept_apart() -> None:
    # docs/security.md narrows its claim to these: a paragraph the sanitiser
    # opens never sits inside another it opened, while nesting the posted
    # markup already had is cleaned as an unrestricted field would clean it.
    field = _restricted(["blockquote"])
    posted = "<p>a<blockquote><h2>b</h2></blockquote>c</p>"
    assert field.clean(posted) == "<p>a<blockquote><p>b</p></blockquote>c</p>"
    assert _restricted([]).clean("<p>a<p>b</p>c</p>") == "<p>a<p>b</p>c</p>"
    # The page's own example: a client <p> in a kept quote in a <p> is left be.
    example = "<p>a<blockquote><p>b</p></blockquote>c</p>"
    assert field.clean(example) == example
    assert TipTapFormField().clean(example) == example
