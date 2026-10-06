from __future__ import annotations

import json

import pytest
from django import forms
from django.core.exceptions import ValidationError
from django.template import Context, Template

from django_tiptap_editor.constants import MAX_DOCUMENT_DEPTH
from django_tiptap_editor.forms.json_field import TipTapJSONFormField
from django_tiptap_editor.types.tiptap_value import TipTapValue

DOC = {"type": "doc", "content": [{"type": "paragraph"}]}


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
