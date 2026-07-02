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
    # get_prep_value returns the {doc, html} mapping; the disallowed mark is gone.
    assert prepared["doc"]["content"][0]["marks"] == []


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


def test_get_prep_value_derives_mirror_when_html_missing() -> None:
    # Programmatic write: doc set, no html → mirror rendered server-side.
    prepared = TipTapJSONField().get_prep_value(TipTapValue.from_stored({"doc": DOC}))
    assert prepared["html"] == "<p>hi</p>"


def test_get_prep_value_rederives_mirror_ignoring_caller_html() -> None:
    # A caller-supplied html mirror is discarded and re-derived from the doc.
    prepared = TipTapJSONField().get_prep_value(
        TipTapValue.from_stored({"doc": DOC, "html": "<p>custom</p>"})
    )
    assert prepared["html"] == "<p>hi</p>"


def test_get_prep_value_discards_hostile_caller_html() -> None:
    # Benign doc, hostile html mirror (an API / import / hand-edit write). The
    # stored mirror must reflect only the sanitized doc, never the caller markup.
    prepared = TipTapJSONField().get_prep_value(
        TipTapValue.from_stored({"doc": DOC, "html": '<img src=x onerror="alert(1)">'})
    )
    assert prepared["html"] == "<p>hi</p>"
    assert "onerror" not in prepared["html"]


def test_get_prep_value_empty_doc_keeps_empty_html() -> None:
    prepared = TipTapJSONField().get_prep_value(TipTapValue.from_stored({"doc": {}, "html": ""}))
    assert prepared["html"] == ""


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
