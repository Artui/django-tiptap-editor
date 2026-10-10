from __future__ import annotations

import copy
from typing import Any

import pytest
from django.core.exceptions import ValidationError

from django_tiptap_editor.constants import MAX_DOCUMENT_DEPTH
from django_tiptap_editor.utils.narrow_doc import narrow_doc
from django_tiptap_editor.utils.sanitize_doc import sanitize_doc


def _text(text: str, *marks: Any) -> dict[str, Any]:
    return {"type": "text", "text": text, **({"marks": list(marks)} if marks else {})}


def _doc(*content: Any) -> dict[str, Any]:
    return {"type": "doc", "content": list(content)}


def _para(*content: Any) -> dict[str, Any]:
    return {"type": "paragraph", **({"content": list(content)} if content else {})}


def test_an_unrestricted_config_returns_the_document_itself() -> None:
    doc = _doc({"type": "heading", "content": [_text("a")]})
    assert narrow_doc(doc, config=None) is doc
    assert narrow_doc(doc, config={"features": None}) is doc


def test_a_restricted_config_leaves_the_document_it_was_given_alone() -> None:
    # docs/api.md says narrow_doc returns a copy: the form field narrows the
    # value the caller posted, which the caller may still be holding.
    color = {"type": "textStyle", "attrs": {"color": "red", "fontSize": "18px"}}
    doc = _doc(
        {"type": "heading", "attrs": {"level": 2, "textAlign": "center"}, "content": [_text("a")]},
        _para(_text("b", {"type": "bold"}, color)),
    )
    before = copy.deepcopy(doc)
    narrowed = narrow_doc(doc, config={"features": ["fontSize"]})
    assert narrowed != before
    assert doc == before


def test_a_value_that_is_not_a_document_is_returned_unchanged() -> None:
    assert narrow_doc("<p>a</p>", config={"features": []}) == "<p>a</p>"


def test_an_empty_heading_becomes_an_empty_paragraph() -> None:
    assert narrow_doc(_doc({"type": "heading"}), config={"features": []}) == _doc(_para())


def test_an_inline_node_the_field_lacks_goes_inside_its_paragraph() -> None:
    image = {"type": "image", "attrs": {"src": "https://example.test/i.png"}}
    doc = _doc(_para(_text("a"), image, _text("b")))
    assert narrow_doc(doc, config={"features": []}) == _doc(_para(_text("a"), _text("b")))
    assert narrow_doc(doc, config={"features": ["image"]}) == doc


def test_a_node_without_a_string_type_is_unwrapped() -> None:
    # A list or object as a type names nothing the field holds.
    doc = _doc({"type": ["heading"], "content": [_para(_text("a"))]})
    assert narrow_doc(doc, config={"features": []}) == _doc(_para(_text("a")))


def test_a_child_that_is_not_a_node_is_left_for_the_renderer() -> None:
    # The renderer skips it, as it does on an unrestricted field.
    assert narrow_doc(_doc("x", _para()), config={"features": []}) == _doc("x", _para())


def test_marks_narrow_with_their_feature() -> None:
    # A mark that never carried a gated attribute is kept as it is, even with
    # no attributes at all; one whose only attribute was gated goes.
    bare = {"type": "textStyle", "attrs": {}}
    coloured = {"type": "textStyle", "attrs": {"color": "red", "fontSize": None}}
    odd = {"type": "link", "attrs": "https://example.test/"}
    doc = _doc(_para(_text("a", bare, odd), _text("b", coloured, "bold")))
    assert narrow_doc(doc, config={"features": ["fontSize", "link"]}) == _doc(
        _para(_text("a", bare, odd), _text("b"))
    )


def test_a_mark_left_with_no_attributes_is_dropped() -> None:
    doc = _doc(_para(_text("a", {"type": "textStyle", "attrs": {"color": "red"}})))
    assert narrow_doc(doc, config={"features": ["fontSize"]}) == _doc(_para(_text("a")))


def _nested(levels: int, *content: Any) -> dict[str, Any]:
    node: dict[str, Any] = {"type": "paragraph", "content": list(content)}
    for _ in range(levels):
        node = {"type": "blockquote", "content": [node]}
    return _doc(node)


def test_the_limit_is_sanitize_docs() -> None:
    # The form field runs sanitize_doc first, so a document it accepts must not
    # be refused here, and one it refuses must be refused here too when
    # narrow_doc is called on its own. Text at the last accepted depth; then an
    # empty content list one level further, which holds no node to refuse; then
    # text there, which does.
    deepest = MAX_DOCUMENT_DEPTH - 3
    config = {"features": []}
    for accepted in (_nested(deepest, _text("x")), _nested(deepest + 1), _nested(deepest + 1, "x")):
        sanitize_doc(accepted)
        narrow_doc(accepted, config=config)
    refused = _nested(deepest + 1, _text("x"))
    with pytest.raises(ValidationError):
        sanitize_doc(refused)
    with pytest.raises(ValidationError, match="nests deeper"):
        narrow_doc(refused, config=config)


def test_a_mark_whose_only_values_are_empty_is_dropped() -> None:
    # An empty string is no more a value than null: a textStyle that kept only
    # an empty fontFamily once its colour went carries nothing.
    style = {"type": "textStyle", "attrs": {"color": "red", "fontFamily": ""}}
    doc = _doc(_para(_text("a", style)))
    assert narrow_doc(doc, config={"features": ["fontFamily"]}) == _doc(_para(_text("a")))


def test_content_freed_inside_a_paragraph_stays_inline() -> None:
    # A custom inline node the field does not name gives up its text in place,
    # inside the paragraph it was in, never as a paragraph nested in it.
    mention = {"type": "mention", "content": [_text("b")]}
    doc = _doc(_para(_text("a"), mention, _text("c")))
    assert narrow_doc(doc, config={"features": []}) == _doc(
        _para(_text("a"), _text("b"), _text("c"))
    )


def test_freed_blocks_keep_their_order_and_their_runs_apart() -> None:
    # Inline content either side of a block freed from the same node makes two
    # paragraphs, not one ahead of the block; a non-node child is kept as is.
    quote = {"type": "blockquote", "content": [_text("a"), _para(_text("b")), "junk", _text("c")]}
    assert narrow_doc(_doc(quote), config={"features": []}) == _doc(
        _para(_text("a")), _para(_text("b")), "junk", _para(_text("c"))
    )


def test_a_document_deeper_than_the_limit_is_refused() -> None:
    # Unwrapped levels recurse too, so the bound holds where nothing is kept.
    doc: dict[str, Any] = _para(_text("x"))
    for _ in range(MAX_DOCUMENT_DEPTH + 1):
        doc = {"type": "blockquote", "content": [doc]}
    with pytest.raises(ValidationError, match="nests deeper"):
        narrow_doc(_doc(doc), config={"features": []})
