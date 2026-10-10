from __future__ import annotations

import json
from typing import Any

import pytest
from django import forms
from django.core.exceptions import ValidationError
from django.template import Context, Template
from django.test import override_settings

from django_tiptap_editor.constants import MAX_DOCUMENT_DEPTH, MAX_JSON_DEPTH, STORAGE_FORMAT_JSON
from django_tiptap_editor.fields.tiptap_json_field import TipTapJSONField
from django_tiptap_editor.forms.fields import TipTapFormField
from django_tiptap_editor.forms.json_field import TipTapJSONFormField
from django_tiptap_editor.types.tiptap_value import TipTapValue
from django_tiptap_editor.utils.render_doc import render_doc
from django_tiptap_editor.utils.resolve_features import resolve_features
from django_tiptap_editor.widgets.tiptap_widget import TipTapWidget

DOC = {"type": "doc", "content": [{"type": "paragraph"}]}


# Bodies ``json.loads`` raises on with something other than JSONDecodeError. The
# decoder's depth limit is the recursion limit on Python 3.10 and 3.11, about ten
# thousand on 3.12 and 3.13, and the C stack on 3.14 (some 74,000 levels on an
# 8 MB stack), so a million levels is past every one of them for a 2 MB string.
# The integer is past the 4300-digit conversion limit Python 3.10.7 introduced.
_UNDECODABLE = [
    pytest.param(
        '{"doc": {"type": "doc", "attrs": ' + "[" * 1_000_000 + "]" * 1_000_000 + '}, "html": ""}',
        RecursionError,
        id="too-deep",
    ),
    pytest.param(
        '{"doc": {"type": "doc", "attrs": {"n": ' + "1" * 5000 + '}}, "html": ""}',
        ValueError,
        id="too-many-digits",
    ),
]


def test_widget_defaults_to_json_storage() -> None:
    assert TipTapJSONFormField().widget.storage == "json"


def test_prepare_value_none_is_empty_string() -> None:
    assert TipTapJSONFormField().prepare_value(None) == ""


def test_prepare_value_serializes_tiptap_value() -> None:
    value = TipTapValue.from_stored({"doc": DOC, "html": "<p></p>"})
    assert json.loads(TipTapJSONFormField().prepare_value(value)) == {"doc": DOC, "html": "<p></p>"}


def test_prepare_value_serializes_dict() -> None:
    assert json.loads(TipTapJSONFormField().prepare_value({"doc": DOC, "html": ""})) == {
        "doc": DOC,
        "html": "",
    }


def test_prepare_value_passes_string_through() -> None:
    assert TipTapJSONFormField().prepare_value('{"doc": {}}') == '{"doc": {}}'


def test_to_python_empty_is_none() -> None:
    field = TipTapJSONFormField(required=False)
    assert field.to_python("") is None
    assert field.to_python(None) is None


def test_to_python_value_passthrough() -> None:
    value = TipTapValue.from_stored({"doc": DOC, "html": "<p></p>"})
    assert TipTapJSONFormField().to_python(value) is value


def test_to_python_parses_envelope() -> None:
    result = TipTapJSONFormField().to_python('{"doc": {"type": "doc"}, "html": "<p>x</p>"}')
    assert isinstance(result, TipTapValue)
    assert result.html == "<p>x</p>"


def test_to_python_rejects_a_value_that_is_not_a_string() -> None:
    # json.loads raises TypeError, not a decode error, on anything but a string.
    with pytest.raises(ValidationError):
        TipTapJSONFormField().to_python(42)


def test_to_python_rejects_invalid_json() -> None:
    with pytest.raises(ValidationError):
        TipTapJSONFormField().to_python("{not json")


class DocumentForm(forms.Form):
    document = TipTapJSONFormField()


PAYLOAD = "<img src=x onerror=alert(document.cookie)>"


def test_a_plain_form_cannot_clean_a_hostile_mirror() -> None:
    # The reproduction: a form with no model behind it reported success and left
    # the client's markup on cleaned_data, marked safe.
    form = DocumentForm(data={"document": json.dumps({"doc": {"type": "doc"}, "html": PAYLOAD})})
    assert form.is_valid()
    assert form.cleaned_data["document"].html == '<img src="x">'
    assert "onerror" not in Template("{{ document }}").render(Context(form.cleaned_data))


def test_the_mirror_is_re_derived_from_the_document() -> None:
    doc = {
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": "x"}]}],
    }
    form = DocumentForm(data={"document": json.dumps({"doc": doc, "html": "<p>lies</p>"})})
    assert form.is_valid()
    assert form.cleaned_data["document"].html == "<p>x</p>"


def test_a_javascript_href_is_stripped_from_the_document() -> None:
    doc = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "x",
                        "marks": [{"type": "link", "attrs": {"href": "javascript:alert(1)"}}],
                    }
                ],
            }
        ],
    }
    form = DocumentForm(data={"document": json.dumps({"doc": doc, "html": ""})})
    assert form.is_valid()
    assert form.cleaned_data["document"].html == "<p>x</p>"


def _text_in(node_type: str, attrs: object, marks: list) -> dict:
    text = {"type": "text", "text": "x", "marks": marks}
    return {"type": "doc", "content": [{"type": node_type, "attrs": attrs, "content": [text]}]}


@pytest.mark.parametrize(
    ("doc", "html"),
    [
        (_text_in("heading", {"level": [2]}, []), "<h1>x</h1>"),
        (_text_in("paragraph", {}, [{"type": ["bold"]}]), "<p>x</p>"),
        (
            _text_in("paragraph", {}, [{"type": "link", "attrs": {"href": "/a", "target": {}}}]),
            '<p><a href="/a">x</a></p>',
        ),
        (_text_in("paragraph", ["textAlign"], []), "<p>x</p>"),
        (_text_in("paragraph", {}, [{"type": "link", "attrs": "/a"}]), "<p><a>x</a></p>"),
    ],
    ids=["heading-level", "mark-type", "link-target", "node-attrs", "mark-attrs"],
)
def test_a_value_of_the_wrong_type_is_skipped_rather_than_a_500(doc: dict, html: str) -> None:
    # Each of these is a crafted POST the editor never sends, and each raised
    # TypeError or AttributeError out of clean(): a 500 for the client rather
    # than a value rendered the way the editor would render it.
    form = DocumentForm(data={"document": json.dumps({"doc": doc, "html": ""})})
    assert form.is_valid()
    assert form.cleaned_data["document"].html == html


@pytest.mark.parametrize("payload", ["[]", '"oops"', "42", "null"])
def test_a_payload_that_is_not_a_document_is_a_field_error(payload: str) -> None:
    # Each of these used to clean successfully into an empty document: the form
    # reported success while discarding the submission.
    form = DocumentForm(data={"document": payload})
    assert not form.is_valid()
    assert form.errors["document"] == ["Enter a valid TipTap document (JSON)."]


def test_a_malformed_envelope_is_a_field_error() -> None:
    form = DocumentForm(data={"document": '{"doc": "oops"}'})
    assert not form.is_valid()
    assert form.errors["document"] == ["Enter a valid TipTap document (JSON)."]


def test_a_deeply_nested_document_is_a_field_error() -> None:
    doc: dict = {"type": "doc"}
    for _ in range(MAX_DOCUMENT_DEPTH + 1):
        doc = {"type": "blockquote", "content": [doc]}
    form = DocumentForm(data={"document": json.dumps({"doc": doc, "html": ""})})
    assert not form.is_valid()
    assert "nests deeper" in form.errors["document"][0]


def _nested_in_attrs(depth: int) -> str:
    """A body whose paragraph's ``attrs`` is ``depth`` nested arrays."""
    attrs = "[" * depth + "]" * depth
    return (
        '{"doc": {"type": "doc", "content": [{"type": "paragraph", "attrs": '
        + attrs
        + '}]}, "html": ""}'
    )


def test_a_body_nested_deep_inside_attrs_is_a_field_error() -> None:
    # It decodes, so the parse guard is not what answers, and it is shallow in
    # content, so neither is sanitize_doc's node limit: the depth is all inside
    # one node's attrs, short of json.loads' own limit even on Python 3.10.
    body = _nested_in_attrs(MAX_JSON_DEPTH + 100)
    json.loads(body)
    form = DocumentForm(data={"document": body})
    assert not form.is_valid()
    assert form.errors["document"] == [
        f"TipTap document nests values deeper than the maximum of {MAX_JSON_DEPTH} levels."
    ]


@pytest.mark.parametrize(("body", "raised"), _UNDECODABLE)
def test_a_body_json_cannot_decode_is_a_field_error_rather_than_a_500(
    body: str, raised: type[Exception]
) -> None:
    # json.loads raises each of these itself, and neither is the JSONDecodeError
    # the parse used to catch, so this is the guard that answers.
    with pytest.raises(raised) as excinfo:
        json.loads(body)
    assert not isinstance(excinfo.value, json.JSONDecodeError)
    form = DocumentForm(data={"document": body})
    assert not form.is_valid()
    assert form.errors["document"] == ["Enter a valid TipTap document (JSON)."]


def _text(text: str, *marks: dict[str, Any]) -> dict[str, Any]:
    return {"type": "text", "text": text, **({"marks": list(marks)} if marks else {})}


def _node(kind: str, *content: dict[str, Any], **attrs: Any) -> dict[str, Any]:
    node: dict[str, Any] = {"type": kind}
    if attrs:
        node["attrs"] = attrs
    if content:
        node["content"] = list(content)
    return node


def _doc(*content: dict[str, Any]) -> dict[str, Any]:
    return _node("doc", *content)


def _para(*content: dict[str, Any], **attrs: Any) -> dict[str, Any]:
    return _node("paragraph", *content, **attrs)


def _restricted(features: list[str] | None, **config: Any) -> TipTapJSONFormField:
    widget = TipTapWidget(config={"features": features, **config}, storage=STORAGE_FORMAT_JSON)
    return TipTapJSONFormField(required=False, widget=widget)


def _clean(features: list[str] | None, doc: dict[str, Any], **config: Any) -> TipTapValue:
    value = _restricted(features, **config).clean(json.dumps({"doc": doc, "html": ""}))
    assert value is not None
    return value


def test_a_restricted_field_narrows_the_document_it_stores() -> None:
    # The document, not only the mirror: the model field re-derives the mirror
    # from the document on every save, so a narrowed mirror alone would be undone.
    doc = _doc(
        _node("heading", _text("Title"), level=2),
        _node("bulletList", _node("listItem", _para(_text("a"))), _node("listItem", _para())),
        _node("table", _node("tableRow", _node("tableCell", _para(_text("cell"))))),
        _node("blockquote", _para(_text("q"))),
        _node("codeBlock", _text("x = 1")),
        _node("horizontalRule"),
    )
    value = _clean(["bold"], doc)
    assert value.doc == _doc(
        _para(_text("Title")),
        _para(_text("a")),
        _para(),
        _para(_text("cell")),
        _para(_text("q")),
        _para(_text("x = 1")),
    )
    assert value.html == "<p>Title</p><p>a</p><p></p><p>cell</p><p>q</p><p>x = 1</p>"


def test_marks_and_attributes_narrow_with_their_feature() -> None:
    style = {"type": "textStyle", "attrs": {"color": "red", "fontSize": "18px"}}
    link = {"type": "link", "attrs": {"href": "https://example.test/"}}
    doc = _doc(_para(_text("a", style, link, {"type": "bold"}), textAlign="center"))
    assert _clean(["fontSize", "bold"], doc).doc == _doc(
        _para(_text("a", {"type": "textStyle", "attrs": {"fontSize": "18px"}}, {"type": "bold"}))
    )
    assert _clean(["textAlign", "link"], doc).doc == _doc(
        _para(_text("a", link), textAlign="center")
    )


def test_a_mark_left_with_no_attributes_is_dropped() -> None:
    # A textStyle mark that only coloured its text has nothing left to say on a
    # field without colour; keeping it would store a span with no style.
    doc = _doc(_para(_text("a", {"type": "textStyle", "attrs": {"color": "red"}})))
    assert _clean(["fontSize"], doc).doc == _doc(_para(_text("a")))


@override_settings(TIPTAP_EXTRA_EXTENSIONS={"callout": {"aside": {}}, "badge": {"mark": {}}})
def test_a_custom_type_survives_only_on_a_field_that_names_it() -> None:
    doc = _doc(_node("callout", _para(_text("a", {"type": "badge"}))))
    assert _clean(["bold"], doc, extensions=["callout", "badge"]).doc == doc
    assert _clean(["bold"], doc, extensions=["badge"]).doc == _doc(
        _para(_text("a", {"type": "badge"}))
    )
    assert _clean(["bold"], doc).doc == _doc(_para(_text("a")))


def test_inline_content_freed_from_a_dropped_node_is_put_in_a_paragraph() -> None:
    # An unknown block holding text directly would otherwise leave text at the
    # top of the document, which no ProseMirror schema accepts.
    doc = _doc(_node("aside", _text("a"), _node("hardBreak"), _text("b")), _para(_text("c")))
    assert _clean([], doc).doc == _doc(
        _para(_text("a"), _node("hardBreak"), _text("b")), _para(_text("c"))
    )


def test_an_unrestricted_field_stores_the_document_as_before() -> None:
    doc = _doc(_node("heading", _text("Title"), level=2, textAlign="center"))
    assert _clean(None, doc).doc == doc


def test_a_mirror_kept_for_an_empty_document_is_narrowed_too() -> None:
    # The one case the mirror is kept rather than re-derived: a row seeded with
    # legacy HTML. Sanitised only globally, it would carry a heading past the
    # field's own features.
    value = _restricted(["bold"]).clean(json.dumps({"doc": {}, "html": "<h2>x</h2>"}))
    assert value is not None
    assert value.html == "<p>x</p>"


@override_settings(TIPTAP_DEFAULT_CONFIG={"features": ["bold"]})
def test_a_widget_that_is_not_tiptap_leaves_the_document_unrestricted() -> None:
    # A plain widget has no config to read features from, so even a project-wide
    # list does not reach it, as for TipTapFormField.
    doc = _doc(_node("heading", _text("Title"), level=2))
    field = TipTapJSONFormField(widget=forms.Textarea)
    value = field.clean(json.dumps({"doc": doc, "html": ""}))
    assert value is not None
    assert value.doc == doc


def test_a_restricted_document_survives_the_model_field_unchanged() -> None:
    # get_prep_value renders the mirror again with global settings; from a
    # narrowed document that rendering is the narrowed one.
    value = _clean(["bold"], _doc(_node("heading", _text("T"), level=1)))
    stored = TipTapJSONField().get_prep_value(value)
    assert stored == {"doc": _doc(_para(_text("T"))), "html": "<p>T</p>"}


_DOC_BATTERY = [
    _doc(_node("heading", _text("A"), level=2), _node("heading", _text("B"), level=3)),
    _doc(
        _node(
            "bulletList",
            _node(
                "listItem",
                _para(_text("a")),
                _node("orderedList", _node("listItem", _para(_text("b")))),
            ),
            _node("listItem", _para(_text("c"))),
        )
    ),
    _doc(
        _node(
            "table",
            _node(
                "tableRow",
                _node("tableHeader", _para(_text("h"))),
                _node("tableCell", _para(_text("c1")), _para(_text("c2"))),
            ),
        )
    ),
    _doc(_node("bulletList", _node("listItem", _node("blockquote", _para(_text("q")))))),
    _doc(
        _node("heading", _text("a", {"type": "bold"}), _text(" b"), level=2),
        _para(_text("c", {"type": "italic"}, {"type": "textStyle", "attrs": {"color": "red"}})),
    ),
    _doc(_node("codeBlock", _text("x")), _para(_text("y"), textAlign="right")),
]


def _types(node: Any) -> set[str]:
    """Every node and mark type in ``node``, the marks of its text included."""
    if not isinstance(node, dict):
        return set()
    found = {node["type"]} | {mark["type"] for mark in node.get("marks", ())}
    for child in node.get("content", ()):
        found |= _types(child)
    return found


_DOC_CONFIGS = [[], ["bold"], ["bulletList", "orderedList"], ["heading", "color"], ["textAlign"]]


@pytest.mark.parametrize("features", _DOC_CONFIGS, ids=lambda f: "+".join(f) or "core")
@pytest.mark.parametrize("doc", _DOC_BATTERY)
def test_the_document_and_the_html_paths_narrow_alike(
    features: list[str], doc: dict[str, Any]
) -> None:
    # What a JSON field stores renders to exactly what an HTML field with the same
    # features keeps of the same content, so the two storage formats cannot
    # disagree about what a field allows. Narrowing is also a fixed point.
    narrowed = _clean(features, doc)
    resolved = resolve_features({"features": features})
    assert resolved is not None
    # Every type in the battery is named after the feature that owns it, but for
    # the document node itself, whose feature is ``document``.
    assert _types(narrowed.doc) <= resolved | {"doc"}
    html_field = TipTapFormField(required=False, widget=TipTapWidget(config={"features": features}))
    assert narrowed.html == html_field.clean(str(render_doc(doc)))
    assert _clean(features, narrowed.doc).doc == narrowed.doc
