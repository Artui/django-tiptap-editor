from __future__ import annotations

import json
from typing import Any

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from django_tiptap_editor.constants import STORAGE_FORMAT_JSON
from django_tiptap_editor.fields.tiptap_json_field import TipTapJSONField
from django_tiptap_editor.forms.fields import TipTapFormField
from django_tiptap_editor.forms.json_field import TipTapJSONFormField
from django_tiptap_editor.templatetags.tiptap import tiptap_html
from django_tiptap_editor.widgets.tiptap_widget import TipTapWidget

GRANT = {"paragraph": ["class"], "heading": ["class"]}
POSTED = '<p class="lead">x</p><h2 class="title">y</h2>'
DOC = {
    "type": "doc",
    "content": [
        {
            "type": "paragraph",
            "attrs": {"class": "lead"},
            "content": [{"type": "text", "text": "x"}],
        },
        {
            "type": "heading",
            "attrs": {"level": 2, "class": "title"},
            "content": [{"type": "text", "text": "y"}],
        },
    ],
}


def _html_field(**config: Any) -> TipTapFormField:
    return TipTapFormField(widget=TipTapWidget(config=config))


def _json_field(**config: Any) -> TipTapJSONFormField:
    return TipTapJSONFormField(widget=TipTapWidget(config=config, storage=STORAGE_FORMAT_JSON))


def _envelope() -> str:
    return json.dumps({"doc": DOC, "html": ""})


PROJECT = override_settings(TIPTAP_DEFAULT_CONFIG={"extraAttributes": GRANT})


@PROJECT
def test_html_storage_keeps_a_granted_class() -> None:
    assert _html_field().clean(POSTED) == POSTED


def test_html_storage_drops_an_ungranted_class() -> None:
    assert _html_field().clean(POSTED) == "<p>x</p><h2>y</h2>"


@PROJECT
def test_a_grant_never_admits_a_tag_the_features_exclude() -> None:
    cleaned = _html_field(features=["bold"]).clean(POSTED)
    assert cleaned == '<p class="lead">x</p><p>y</p>'


@PROJECT
def test_a_field_narrows_the_project_grant_by_type_or_to_nothing() -> None:
    cleaned = _html_field(extraAttributes={"heading": ["class"]}).clean(POSTED)
    assert cleaned == '<p>x</p><h2 class="title">y</h2>'
    assert _html_field(extraAttributes={}).clean(POSTED) == "<p>x</p><h2>y</h2>"


def test_a_field_cannot_widen_the_project_grant() -> None:
    with pytest.raises(ImproperlyConfigured, match=r"paragraph\.class.*narrow the project"):
        _html_field(extraAttributes=GRANT).clean(POSTED)


@PROJECT
def test_json_storage_form_keeps_a_granted_class_in_doc_and_mirror() -> None:
    value = _json_field().clean(_envelope())
    assert value.doc == DOC
    assert value.html == POSTED


def test_json_storage_form_mirror_drops_an_ungranted_class_and_the_doc_keeps_it() -> None:
    value = _json_field().clean(_envelope())
    assert value.doc == DOC
    assert value.html == "<p>x</p><h2>y</h2>"


@override_settings(TIPTAP_DEFAULT_CONFIG={"extraAttributes": GRANT})
def test_the_model_field_renders_the_project_grant() -> None:
    stored = TipTapJSONField().get_prep_value({"doc": DOC, "html": ""})
    assert stored["doc"] == DOC
    assert stored["html"] == POSTED


def test_the_model_field_without_a_project_grant_renders_no_class() -> None:
    stored = TipTapJSONField().get_prep_value({"doc": DOC, "html": ""})
    assert stored["html"] == "<p>x</p><h2>y</h2>"


def test_the_model_field_accepts_a_granted_attribute() -> None:
    TipTapJSONField().validate({"doc": DOC, "html": POSTED}, None)


@override_settings(TIPTAP_DEFAULT_CONFIG={"extraAttributes": GRANT})
def test_the_html_filter_renders_a_raw_doc_and_keeps_stored_html_with_the_project_grant() -> None:
    assert tiptap_html(DOC) == POSTED
    assert tiptap_html(POSTED) == POSTED


@PROJECT
def test_a_per_field_grant_saves_through_the_model_with_the_mirror_the_form_built() -> None:
    for grant in ({"heading": ["class"]}, {}):
        value = _json_field(extraAttributes=grant).clean(_envelope())
        stored = TipTapJSONField().get_prep_value(value)
        assert stored == {"doc": DOC, "html": POSTED}
        assert value.html == POSTED


def test_a_per_field_grant_the_model_could_not_render_is_refused_before_saving() -> None:
    with pytest.raises(ImproperlyConfigured, match="narrow the project"):
        _json_field(extraAttributes=GRANT).clean(_envelope())
