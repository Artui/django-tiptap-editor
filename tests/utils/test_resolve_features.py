from __future__ import annotations

import pytest

from django_tiptap_editor.constants import BUILTIN_EXTENSIONS, FEATURE_CORE
from django_tiptap_editor.utils import resolve_features as reexported
from django_tiptap_editor.utils.resolve_features import resolve_features


def test_no_features_key_is_no_restriction() -> None:
    assert resolve_features({}) is None
    assert resolve_features({"height": "300px", "extensions": ["callout"]}) is None


def test_features_none_is_no_restriction() -> None:
    assert resolve_features({"features": None}) is None


def test_an_empty_list_is_the_core_alone() -> None:
    assert resolve_features({"features": []}) == FEATURE_CORE


def test_a_table_pulls_its_rows_cells_and_headers() -> None:
    assert resolve_features({"features": ["table"]}) == FEATURE_CORE | {
        "table",
        "tableRow",
        "tableCell",
        "tableHeader",
    }


def test_highlight_pulls_background_color_and_text_style() -> None:
    assert resolve_features({"features": ["highlight"]}) == FEATURE_CORE | {
        "highlight",
        "backgroundColor",
        "textStyle",
    }


@pytest.mark.parametrize("name", ["bulletList", "orderedList"])
def test_a_list_pulls_list_item(name: str) -> None:
    assert resolve_features({"features": [name]}) == FEATURE_CORE | {name, "listItem"}


def test_a_feature_with_no_dependencies_is_itself_plus_core() -> None:
    assert resolve_features({"features": ["heading"]}) == FEATURE_CORE | {"heading"}


def test_duplicates_collapse() -> None:
    assert resolve_features({"features": ["bold", "bold", "table", "table"]}) == resolve_features(
        {"features": ["bold", "table"]}
    )


def test_order_does_not_matter() -> None:
    names = ["highlight", "table", "bulletList", "link", "color"]
    assert resolve_features({"features": names}) == resolve_features(
        {"features": list(reversed(names))}
    )


def test_core_is_present_whatever_is_listed() -> None:
    for names in ([], ["bold"], ["paragraph"], sorted(BUILTIN_EXTENSIONS)):
        resolved = resolve_features({"features": names})
        assert resolved is not None
        assert resolved >= FEATURE_CORE


def test_listing_every_feature_is_every_built_in() -> None:
    assert resolve_features({"features": sorted(BUILTIN_EXTENSIONS)}) == BUILTIN_EXTENSIONS


def test_the_result_is_frozen() -> None:
    assert isinstance(resolve_features({"features": ["bold"]}), frozenset)


def test_the_input_list_is_not_mutated() -> None:
    names = ["table", "highlight"]
    resolve_features({"features": names})
    assert names == ["table", "highlight"]


def test_it_is_reexported_from_utils() -> None:
    assert reexported is resolve_features
