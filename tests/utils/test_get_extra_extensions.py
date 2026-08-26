from __future__ import annotations

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from django_tiptap_editor.utils.get_extra_extensions import get_extra_extensions


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
