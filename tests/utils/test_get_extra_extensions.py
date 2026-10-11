from __future__ import annotations

from collections.abc import Callable

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.test import override_settings

from django_tiptap_editor.forms.fields import TipTapFormField
from django_tiptap_editor.templatetags.tiptap import tiptap_html
from django_tiptap_editor.types.tiptap_value import TipTapValue
from django_tiptap_editor.utils.get_extra_extensions import get_extra_extensions
from django_tiptap_editor.widgets.tiptap_widget import TipTapWidget
from tests.testapp.models import Article


def test_default_is_empty() -> None:
    assert get_extra_extensions() == {}


@override_settings(TIPTAP_EXTRA_EXTENSIONS=["myExt", "other"])
def test_list_form_leaves_the_vocabulary_undeclared() -> None:
    assert get_extra_extensions() == {"myExt": None, "other": None}


@override_settings(
    TIPTAP_EXTRA_EXTENSIONS={
        "callout": {"DIV": {"attrs": ["Class"], "styles": ["background-color"]}},
        "shortcut": {},
    }
)
def test_mapping_form_normalizes_the_declared_vocabulary() -> None:
    assert get_extra_extensions() == {
        "callout": {"div": {"attrs": ("class",), "styles": ("background-color",)}},
        "shortcut": {},
    }


@override_settings(TIPTAP_EXTRA_EXTENSIONS={"callout": {"div": {}}})
def test_mapping_form_allows_a_tag_with_no_attributes() -> None:
    assert get_extra_extensions() == {"callout": {"div": {}}}


@override_settings(TIPTAP_EXTRA_EXTENSIONS={"callout": ["div"]})
def test_rejects_a_non_mapping_vocabulary() -> None:
    with pytest.raises(ImproperlyConfigured, match="must map a tag name"):
        get_extra_extensions()


@override_settings(TIPTAP_EXTRA_EXTENSIONS={"callout": {"a b": {}}})
def test_rejects_an_invalid_tag_name() -> None:
    with pytest.raises(ImproperlyConfigured, match="invalid tag"):
        get_extra_extensions()


@override_settings(TIPTAP_EXTRA_EXTENSIONS={"callout": {"script": {}}})
def test_rejects_a_tag_that_executes_script() -> None:
    with pytest.raises(ImproperlyConfigured, match="executes script"):
        get_extra_extensions()


# A browser reads the content of each of these by rules of its own (raw text,
# escapable raw text, or MathML's namespace) where html.parser reads markup, so a
# kept one would be stored as one thing and rendered as another.
@pytest.mark.parametrize(
    "tag", ["math", "noembed", "noframes", "plaintext", "textarea", "title", "xmp"]
)
def test_rejects_a_tag_whose_content_a_browser_parses_differently(tag: str) -> None:
    declared = {"formula": {tag: {"attrs": ["class"]}}}
    with (
        override_settings(TIPTAP_EXTRA_EXTENSIONS=declared),
        pytest.raises(ImproperlyConfigured, match=f"declares the tag '{tag}', whose content"),
    ):
        get_extra_extensions()


# Where a project that declares one of those tags finds out. The setting is read
# when it is used, not when Django starts, so the system checks pass and the
# error is raised by the first request that cleans, renders or validates TipTap
# content; docs/extending.md lists these places.
_REFUSED = {"formula": {"math": {"attrs": ["class"]}}}
_EMPTY_DOC = {"doc": {"type": "doc", "content": []}}


def _clean_a_form_field() -> None:
    TipTapFormField().clean("<p>x</p>")


def _render_the_filter() -> None:
    tiptap_html("<p>x</p>")


def _render_a_widget_naming_the_extension() -> None:
    TipTapWidget(config={"extensions": ["formula"]}).render("body", "")


def _validate_a_json_field() -> None:
    Article(title="t", body="b", document=TipTapValue.from_stored(_EMPTY_DOC)).full_clean()


@pytest.mark.django_db
@override_settings(TIPTAP_EXTRA_EXTENSIONS=_REFUSED)
@pytest.mark.parametrize(
    "use",
    [
        _clean_a_form_field,
        _render_the_filter,
        _render_a_widget_naming_the_extension,
        _validate_a_json_field,
    ],
)
def test_a_refused_tag_is_reported_where_the_setting_is_read(use: Callable[[], None]) -> None:
    with pytest.raises(ImproperlyConfigured, match="declares the tag 'math', whose content"):
        use()


@pytest.mark.django_db
@override_settings(TIPTAP_EXTRA_EXTENSIONS=_REFUSED)
def test_a_refused_tag_is_not_reported_where_the_setting_is_not_read() -> None:
    call_command("check")
    TipTapWidget().render("body", "")
    tiptap_html(TipTapValue.from_stored(_EMPTY_DOC))


@override_settings(TIPTAP_EXTRA_EXTENSIONS={"callout": {"div": {"class": ["x"]}}})
def test_rejects_an_unknown_vocabulary_key() -> None:
    with pytest.raises(ImproperlyConfigured, match="must be a mapping with keys"):
        get_extra_extensions()


@override_settings(TIPTAP_EXTRA_EXTENSIONS={"callout": {"div": {"attrs": "class"}}})
def test_rejects_a_string_where_a_list_belongs() -> None:
    with pytest.raises(ImproperlyConfigured, match="must be a list of strings"):
        get_extra_extensions()


@override_settings(TIPTAP_EXTRA_EXTENSIONS={"callout": {"div": {"attrs": ["onclick"]}}})
def test_rejects_an_event_handler_attribute() -> None:
    with pytest.raises(ImproperlyConfigured, match="event-handler"):
        get_extra_extensions()
