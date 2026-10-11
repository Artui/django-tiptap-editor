from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any

import pytest
from django.test import override_settings

from django_tiptap_editor.constants import (
    BLOCK_STYLE_PROPERTIES,
    DEFAULT_IMAGE_PROTOCOLS,
    DEFAULT_LINK_PROTOCOLS,
    EXTENSION_HTML_VOCABULARY,
    PARAGRAPH_BLOCK_TAGS,
)
from django_tiptap_editor.types.html_schema import HtmlSchema
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


# Taken from get_html_schema() before it accepted a config, so an unrestricted
# field is held to the allowlist it has always had, byte for byte.
_SNAPSHOT = json.loads(
    (
        Path(__file__).resolve().parent.parent / "fixtures" / "unrestricted_html_schema.json"
    ).read_text(encoding="utf-8")
)


def _dump(schema: HtmlSchema) -> dict[str, Any]:
    return {
        "tags": {tag: sorted(names) for tag, names in sorted(schema.tags.items())},
        "styles": {tag: sorted(props) for tag, props in sorted(schema.styles.items())},
        "link_protocols": list(schema.link_protocols),
        "image_protocols": list(schema.image_protocols),
    }


@pytest.mark.parametrize(
    "config", [None, {}, {"toolbar": [["bold"]]}, {"features": None}], ids=repr
)
def test_a_config_without_features_gets_the_schema_it_always_had(
    config: dict[str, Any] | None,
) -> None:
    schema = get_html_schema(config)
    assert _dump(schema) == _SNAPSHOT["builtin"]
    # Nothing is converted on an unrestricted field: every block is allowed.
    assert schema.paragraph_blocks == frozenset()
    with override_settings(TIPTAP_EXTRA_EXTENSIONS={"callout": {"aside": {"attrs": ["class"]}}}):
        assert _dump(get_html_schema(config)) == _SNAPSHOT["with_callout"]


def test_features_admit_only_the_vocabularies_of_the_resolved_set() -> None:
    schema = get_html_schema({"features": ["bulletList", "link"]})
    # bulletList pulls in listItem; the core brings paragraphs and line breaks.
    assert set(schema.tags) == {"p", "br", "ul", "li", "a"}
    assert schema.attributes("a") == frozenset({"class", "href", "rel", "target", "title"})
    assert schema.style_properties("p") == frozenset(BLOCK_STYLE_PROPERTIES)


def test_an_attribute_feature_decorates_tags_without_admitting_them() -> None:
    schema = get_html_schema({"features": ["textAlign", "fontSize"]})
    assert not schema.allows("h2")
    assert schema.style_properties("p") == frozenset(BLOCK_STYLE_PROPERTIES) | {"text-align"}
    assert schema.style_properties("span") == frozenset({"font-size"})
    # With headings on, the same feature reaches them.
    with_headings = get_html_schema({"features": ["textAlign", "heading"]})
    assert "text-align" in with_headings.style_properties("h2")


def test_blocks_the_field_lacks_are_the_ones_converted_to_paragraphs() -> None:
    assert get_html_schema({"features": ["heading", "bulletList"]}).paragraph_blocks == (
        PARAGRAPH_BLOCK_TAGS - {f"h{level}" for level in range(1, 7)} - {"li"}
    )


@override_settings(
    TIPTAP_EXTRA_EXTENSIONS={"callout": {"aside": {}}, "badge": {"mark": {"attrs": ["class"]}}}
)
def test_a_restricted_schema_takes_only_the_extensions_its_config_names() -> None:
    schema = get_html_schema({"features": [], "extensions": ["badge"]})
    assert schema.allows("mark")
    assert not schema.allows("aside")
    assert not get_html_schema({"features": []}).allows("mark")


@override_settings(TIPTAP_EXTRA_EXTENSIONS=["callout", "legacy"])
def test_only_an_included_undeclared_extension_warns() -> None:
    with pytest.warns(UserWarning) as record:
        get_html_schema({"features": [], "extensions": ["legacy"]})
    assert [str(warning.message).split()[2] for warning in record] == ["'legacy'"]


@override_settings(TIPTAP_DEFAULT_CONFIG={"linkProtocols": ["https", "mailto"]})
def test_link_protocols_come_from_the_project_not_the_field() -> None:
    # docs/security.md states this as a limit: a field's own linkProtocols
    # restricts its editor, and the server keeps reading the project default.
    schema = get_html_schema({"features": ["link"], "linkProtocols": ["https"]})
    assert schema.link_protocols == ("https", "mailto")
