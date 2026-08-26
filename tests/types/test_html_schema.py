from __future__ import annotations

from django_tiptap_editor.types.html_schema import HtmlSchema

SCHEMA = HtmlSchema(tags={"p": frozenset({"id"})}, styles={"p": frozenset({"color"})})


def test_allows_only_declared_tags() -> None:
    assert SCHEMA.allows("p")
    assert not SCHEMA.allows("div")


def test_attributes_of_an_unknown_tag_are_empty() -> None:
    assert SCHEMA.attributes("p") == frozenset({"id"})
    assert SCHEMA.attributes("div") == frozenset()


def test_style_properties_of_an_unknown_tag_are_empty() -> None:
    assert SCHEMA.style_properties("p") == frozenset({"color"})
    assert SCHEMA.style_properties("div") == frozenset()
