from __future__ import annotations

import pytest

from django_tiptap_editor.fields.tiptap_json_field import TipTapJSONField
from django_tiptap_editor.forms.json_field import TipTapJSONFormField
from django_tiptap_editor.types.tiptap_value import TipTapValue
from tests.testapp.models import Article

DOC = {
    "type": "doc",
    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "hi"}]}],
}


def test_to_python_passthrough_and_none() -> None:
    field = TipTapJSONField()
    value = TipTapValue.from_stored({"doc": DOC, "html": "<p>hi</p>"})
    assert field.to_python(value) is value
    assert field.to_python(None) is None


def test_to_python_parses_str_and_dict() -> None:
    field = TipTapJSONField()
    from_str = field.to_python('{"doc": {"type": "doc"}, "html": "<p></p>"}')
    from_dict = field.to_python({"doc": {"type": "doc"}, "html": "<p></p>"})
    assert isinstance(from_str, TipTapValue)
    assert from_dict.doc == {"type": "doc"}


def test_get_prep_value_none() -> None:
    assert TipTapJSONField().get_prep_value(None) is None


def test_get_prep_value_sanitizes_doc() -> None:
    field = TipTapJSONField()
    evil = {
        "type": "doc",
        "content": [
            {
                "type": "text",
                "text": "x",
                "marks": [{"type": "link", "attrs": {"href": "javascript:alert(1)"}}],
            }
        ],
    }
    prepared = field.get_prep_value(TipTapValue.from_stored({"doc": evil, "html": "<p>x</p>"}))
    # JSONField serializes to a JSON string; the disallowed link mark is gone.
    assert "javascript:" not in prepared


def test_formfield_uses_json_form_field() -> None:
    field = TipTapJSONField()
    form_field = field.formfield()
    assert isinstance(form_field, TipTapJSONFormField)
    assert form_field.widget.storage == "json"


@pytest.mark.django_db
def test_db_roundtrip_returns_tiptap_value() -> None:
    article = Article.objects.create(
        title="t",
        body="",
        document=TipTapValue.from_stored({"doc": DOC, "html": "<p>hi</p>"}),
    )
    reloaded = Article.objects.get(pk=article.pk)
    assert isinstance(reloaded.document, TipTapValue)
    assert reloaded.document.doc == DOC
    assert reloaded.document.html == "<p>hi</p>"


@pytest.mark.django_db
def test_db_roundtrip_null() -> None:
    article = Article.objects.create(title="t", body="", document=None)
    assert Article.objects.get(pk=article.pk).document is None


@pytest.mark.django_db
def test_db_save_strips_disallowed_link() -> None:
    evil = {
        "type": "doc",
        "content": [
            {
                "type": "text",
                "text": "x",
                "marks": [{"type": "link", "attrs": {"href": "javascript:alert(1)"}}],
            }
        ],
    }
    article = Article.objects.create(
        title="t", body="", document=TipTapValue.from_stored({"doc": evil, "html": "<p>x</p>"})
    )
    doc = Article.objects.get(pk=article.pk).document.doc
    assert doc["content"][0]["marks"] == []
