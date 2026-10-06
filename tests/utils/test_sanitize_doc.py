from __future__ import annotations

import json
from pathlib import Path

import pytest
from django.core.exceptions import ValidationError

from django_tiptap_editor.constants import MAX_DOCUMENT_DEPTH
from django_tiptap_editor.utils.render_doc import render_doc
from django_tiptap_editor.utils.sanitize_doc import sanitize_doc


def _link(href: str) -> dict:
    return {"type": "text", "text": "x", "marks": [{"type": "link", "attrs": {"href": href}}]}


def test_non_dict_returned_unchanged() -> None:
    assert sanitize_doc(None) is None
    assert sanitize_doc("text") == "text"


def test_keeps_allowed_link_href() -> None:
    node = {
        "type": "text",
        "text": "x",
        "marks": [{"type": "link", "attrs": {"href": "https://ok"}}],
    }
    assert sanitize_doc(node)["marks"] == node["marks"]


def test_drops_disallowed_link_href() -> None:
    node = {
        "type": "text",
        "text": "x",
        "marks": [{"type": "link", "attrs": {"href": "javascript:alert(1)"}}],
    }
    assert sanitize_doc(node)["marks"] == []


@pytest.mark.parametrize("attrs", [["href", "javascript:alert(1)"], "javascript:alert(1)", 1])
def test_a_link_whose_attrs_are_not_a_mapping_is_kept_as_one_with_no_url(attrs: object) -> None:
    # The editor reads such a link as one with no href, so there is no URL to
    # refuse and the mark stays; reading .get off it raised AttributeError. The
    # renderer emits it with no href either, so nothing in it reaches the page.
    node = {"type": "text", "text": "x", "marks": [{"type": "link", "attrs": attrs}]}
    assert sanitize_doc(node)["marks"] == node["marks"]
    doc = {"type": "doc", "content": [{"type": "paragraph", "content": [node]}]}
    assert render_doc(doc) == "<p><a>x</a></p>"


def test_only_a_link_is_dropped_for_its_href() -> None:
    # The href is read only off a link: no other mark renders one, so dropping
    # a bold mark that happens to carry a hostile href would lose the formatting
    # and protect nothing.
    node = {
        "type": "text",
        "text": "x",
        "marks": [{"type": "bold", "attrs": {"href": "javascript:alert(1)"}}],
    }
    assert sanitize_doc(node)["marks"] == node["marks"]


def test_keeps_relative_link_and_other_marks() -> None:
    node = {
        "type": "text",
        "text": "x",
        "marks": [
            {"type": "bold"},
            {"type": "link", "attrs": {"href": "/relative"}},
            {"type": "link"},  # no attrs → no scheme → allowed
            "not-a-dict",  # tolerated, kept
        ],
    }
    assert sanitize_doc(node)["marks"] == node["marks"]


def test_blanks_disallowed_image_src() -> None:
    node = {"type": "image", "attrs": {"src": "javascript:alert(1)", "alt": "a"}}
    out = sanitize_doc(node)
    assert out["attrs"]["src"] == ""
    assert out["attrs"]["alt"] == "a"


def test_keeps_allowed_and_data_image_src() -> None:
    https = {"type": "image", "attrs": {"src": "https://img/x.png"}}
    data = {"type": "image", "attrs": {"src": "data:image/png;base64,AAAA"}}
    assert sanitize_doc(https)["attrs"]["src"] == "https://img/x.png"
    assert sanitize_doc(data)["attrs"]["src"].startswith("data:")


def test_image_without_attrs_is_untouched() -> None:
    node = {"type": "image"}
    assert sanitize_doc(node) == {"type": "image"}


def test_recurses_into_content() -> None:
    doc = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "x",
                        "marks": [{"type": "link", "attrs": {"href": "javascript:x"}}],
                    },
                    {"type": "image", "attrs": {"src": "vbscript:x"}},
                ],
            }
        ],
    }
    out = sanitize_doc(doc)
    para = out["content"][0]["content"]
    assert para[0]["marks"] == []
    assert para[1]["attrs"]["src"] == ""


def test_custom_protocol_allowlist() -> None:
    node = {"type": "text", "marks": [{"type": "link", "attrs": {"href": "ftp://host"}}]}
    assert sanitize_doc(node, link_protocols=("ftp",))["marks"] == node["marks"]


@pytest.mark.parametrize(
    "href",
    [
        "java\nscript:alert(1)",  # embedded newline
        "java\tscript:alert(1)",  # embedded tab
        "jav\rascript:alert(1)",  # embedded carriage return
        "\x01javascript:alert(1)",  # leading C0 control
        "  javascript:alert(1)",  # leading spaces
        "JaVaScRiPt:alert(1)",  # mixed case
        "\x0cJAVA\nSCRIPT:x",  # form-feed + newline, mixed case
    ],
)
def test_drops_javascript_href_hidden_by_whitespace_or_control_chars(href: str) -> None:
    # A browser strips whitespace/control chars while resolving the URL, so these
    # all execute as ``javascript:`` on click — the scheme must be seen and dropped.
    assert sanitize_doc(_link(href))["marks"] == []


def test_blanks_image_src_scheme_hidden_by_whitespace() -> None:
    node = {"type": "image", "attrs": {"src": "java\nscript:alert(1)"}}
    assert sanitize_doc(node)["attrs"]["src"] == ""


def test_keeps_entity_and_percent_encoded_forms_verbatim() -> None:
    # These carry no literal scheme (``&``/``%`` prefix), so sanitize keeps them;
    # render_doc's HTML-escaping is what neutralizes them on output — the browser
    # never re-decodes an escaped attribute into an executable scheme.
    for href in ["&#106;avascript:alert(1)", "%6aavascript:alert(1)"]:
        assert sanitize_doc(_link(href))["marks"] == _link(href)["marks"]


def _nest(depth: int) -> dict:
    doc: dict = {"type": "doc"}
    for _ in range(depth):
        doc = {"type": "blockquote", "content": [doc]}
    return doc


def test_a_document_at_the_depth_limit_is_accepted() -> None:
    assert sanitize_doc(_nest(MAX_DOCUMENT_DEPTH - 1)) is not None


def test_a_deeper_document_is_refused_before_it_costs_the_stack() -> None:
    # A few kilobytes of nesting used to reach the renderer and raise
    # RecursionError out of a save: a 500 rather than a field error.
    with pytest.raises(ValidationError, match="nests deeper"):
        sanitize_doc(_nest(MAX_DOCUMENT_DEPTH + 1))


def test_the_renderer_refuses_it_too() -> None:
    with pytest.raises(ValidationError, match="nests deeper"):
        render_doc(_nest(MAX_DOCUMENT_DEPTH + 1))


def test_attributes_that_carry_no_url_pass_through_for_the_renderer_to_gate() -> None:
    # sanitize_doc secures URL-bearing attributes and nesting depth, nothing
    # else; render_doc decides what every other stored attribute becomes. So a
    # link title and a cell alignment, including one Tiptap would not render,
    # are stored as the editor wrote them, and test_render_doc holds the
    # renderer to the editor's output for each.
    cases = json.loads(
        (Path(__file__).parent / "fixtures" / "editor_render.json").read_text(encoding="utf-8")
    )["cases"]
    for case in cases:
        assert sanitize_doc(case["doc"]) == case["doc"]
