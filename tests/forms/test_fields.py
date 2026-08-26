from __future__ import annotations

import pytest
from django import forms
from django.core.exceptions import ValidationError
from django.template import Context, Template

from django_tiptap_editor.constants import MAX_DOCUMENT_DEPTH
from django_tiptap_editor.forms.fields import TipTapFormField
from django_tiptap_editor.widgets.tiptap_widget import TipTapWidget

PAYLOAD = "<img src=x onerror=alert(document.cookie)>"


class ArticleForm(forms.Form):
    body = TipTapFormField()


def test_default_widget_is_tiptap() -> None:
    assert isinstance(TipTapFormField().widget, TipTapWidget)


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
