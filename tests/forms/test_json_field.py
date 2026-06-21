from __future__ import annotations

import json

import pytest
from django.core.exceptions import ValidationError

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
