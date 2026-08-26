from __future__ import annotations

import warnings

import pytest
from django.test import override_settings

from django_tiptap_editor.constants import (
    DEFAULT_IMAGE_PROTOCOLS,
    DEFAULT_LINK_PROTOCOLS,
    EXTENSION_HTML_VOCABULARY,
)
from django_tiptap_editor.utils.get_html_schema import get_html_schema


def test_the_schema_is_the_union_of_the_builtin_vocabularies() -> None:
    schema = get_html_schema()
    declared = {tag for vocabulary in EXTENSION_HTML_VOCABULARY.values() for tag in vocabulary}
    assert set(schema.tags) == declared


def test_extensions_contributing_to_one_tag_are_merged() -> None:
    # color, fontSize, fontFamily and the highlight all write their own
    # declaration onto the same <span>.
    assert get_html_schema().style_properties("span") == frozenset(
        {"background-color", "color", "font-family", "font-size"}
    )


def test_protocols_default_to_the_package_allowlists() -> None:
    schema = get_html_schema()
    assert schema.link_protocols == DEFAULT_LINK_PROTOCOLS
    assert schema.image_protocols == DEFAULT_IMAGE_PROTOCOLS


@override_settings(TIPTAP_DEFAULT_CONFIG={"linkProtocols": ["https", "mailto"]})
def test_configured_link_protocols_are_used() -> None:
    assert get_html_schema().link_protocols == ("https", "mailto")


@override_settings(TIPTAP_EXTRA_EXTENSIONS={"callout": {"aside": {"attrs": ["class"]}}})
def test_a_declared_custom_extension_joins_the_allowlist() -> None:
    schema = get_html_schema()
    assert schema.allows("aside")
    assert schema.attributes("aside") == frozenset({"class"})


@override_settings(TIPTAP_EXTRA_EXTENSIONS={"shortcut": {}})
def test_an_extension_that_declares_no_markup_is_silent() -> None:
    # An extension can legitimately emit nothing (a keyboard shortcut, a
    # counter). Declaring that explicitly is how a project says so.
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        get_html_schema()


@override_settings(TIPTAP_EXTRA_EXTENSIONS=["callout"])
def test_an_undeclared_extension_warns_and_names_itself() -> None:
    with pytest.warns(UserWarning, match="TIPTAP_EXTRA_EXTENSIONS"):
        schema = get_html_schema()
    assert not schema.allows("aside")
