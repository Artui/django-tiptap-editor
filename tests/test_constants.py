"""The feature model is consistent with the vocabulary it restricts.

``FEATURE_CORE`` and ``FEATURE_DEPENDENCIES`` are hand-written beside
``EXTENSION_HTML_VOCABULARY``, and nothing else would notice them drifting: a
renamed extension leaves a dependency naming nothing, and a new ``span`` mark
added without its ``textStyle`` dependency mounts a mark whose wrapper is not
in the schema. Each check here is one of those silent failures.
"""

from __future__ import annotations

import pytest

from django_tiptap_editor.constants import (
    BUILTIN_EXTENSIONS,
    DECORATING_FEATURES,
    DOCUMENT_FEATURES,
    EXTENSION_HTML_VOCABULARY,
    FEATURE_CORE,
    FEATURE_DEPENDENCIES,
    KNOWN_CONFIG_KEYS,
    PARAGRAPH_BLOCK_TAGS,
)
from django_tiptap_editor.fields.tiptap_json_field import (
    _RENDERABLE_MARK_TYPES,
    _RENDERABLE_NODE_TYPES,
)
from django_tiptap_editor.utils.resolve_features import resolve_features


def _closure(name: str) -> frozenset[str]:
    resolved = resolve_features({"features": [name]})
    assert resolved is not None
    return resolved


def _emitters(tag: str) -> set[str]:
    """Return every built-in extension whose vocabulary declares ``tag``."""
    return {name for name, vocabulary in EXTENSION_HTML_VOCABULARY.items() if tag in vocabulary}


def test_features_is_a_known_config_key() -> None:
    assert "features" in KNOWN_CONFIG_KEYS


def test_core_is_built_in() -> None:
    assert FEATURE_CORE <= BUILTIN_EXTENSIONS


def test_core_carries_the_document_structure_and_line_breaks() -> None:
    assert {"document", "text", "paragraph", "hardBreak"} <= FEATURE_CORE


def test_every_dependency_key_and_value_is_built_in() -> None:
    for name, deps in FEATURE_DEPENDENCIES.items():
        assert name in BUILTIN_EXTENSIONS, name
        assert set(deps) <= BUILTIN_EXTENSIONS, (name, deps)


def test_no_dependency_key_or_value_is_core() -> None:
    # A core key would never be walked (the resolver starts from core and skips
    # what it has seen), so its dependencies would silently never be pulled in.
    for name, deps in FEATURE_DEPENDENCIES.items():
        assert name not in FEATURE_CORE, name
        assert not set(deps) & FEATURE_CORE, (name, deps)


def test_no_feature_depends_on_itself() -> None:
    for name, deps in FEATURE_DEPENDENCIES.items():
        assert name not in deps, name


@pytest.mark.parametrize("name", sorted(BUILTIN_EXTENSIONS))
def test_every_closure_stays_inside_the_built_ins(name: str) -> None:
    assert _closure(name) <= BUILTIN_EXTENSIONS


@pytest.mark.parametrize("name", sorted(_emitters("span") - {"textStyle"}))
def test_every_span_mark_pulls_text_style(name: str) -> None:
    # Derived from the vocabulary, so a new span mark is checked the day it is
    # added: textStyle is the mark the others render through.
    assert "textStyle" in _closure(name)


@pytest.mark.parametrize(
    ("parent", "children"),
    [("ul", ("li",)), ("ol", ("li",)), ("table", ("tr", "td", "th"))],
)
def test_a_container_pulls_the_extensions_emitting_its_children(
    parent: str, children: tuple[str, ...]
) -> None:
    for container in _emitters(parent):
        for child in children:
            assert _emitters(child) <= _closure(container), (container, child)


def test_the_paragraph_blocks_are_built_in_tags() -> None:
    assert all(_emitters(tag) for tag in PARAGRAPH_BLOCK_TAGS)


def test_the_document_table_names_exactly_the_types_the_renderer_draws() -> None:
    # The renderer and the model field's validation already enumerate the node
    # and mark types a stored document may carry; narrowing has to place each of
    # them, and must not invent one. The editor's own schema is held to the same
    # table in js/test/html-vocabulary.test.ts.
    types = {key for key in DOCUMENT_FEATURES if "." not in key}
    assert types == _RENDERABLE_NODE_TYPES | _RENDERABLE_MARK_TYPES


def test_the_document_table_maps_onto_built_in_features() -> None:
    assert set(DOCUMENT_FEATURES.values()) <= BUILTIN_EXTENSIONS
    for key, feature in DOCUMENT_FEATURES.items():
        owner, _, attribute = key.partition(".")
        assert owner in DOCUMENT_FEATURES, key
        # An attribute entry exists to name a feature other than its type's.
        assert not attribute or feature != DOCUMENT_FEATURES[owner], key


def test_the_decorating_features_are_the_attribute_only_ones() -> None:
    assert {"backgroundColor", "color", "fontFamily", "fontSize", "textAlign"} == (
        DECORATING_FEATURES
    )
