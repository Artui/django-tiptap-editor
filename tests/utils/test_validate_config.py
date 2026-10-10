from __future__ import annotations

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from django_tiptap_editor.utils.validate_config import validate_config


def test_valid_config_passes_through() -> None:
    cfg = {"height": "550px", "extensions": ["bold", "italic"]}
    assert validate_config(cfg) is cfg


def test_no_extensions_key_is_fine() -> None:
    assert validate_config({"height": "1px"}) == {"height": "1px"}


def test_unknown_top_level_key_raises() -> None:
    with pytest.raises(ImproperlyConfigured, match="Unknown TipTap config key"):
        validate_config({"heigth": "1px"})


def test_unknown_extension_raises() -> None:
    with pytest.raises(ImproperlyConfigured, match="Unknown TipTap extension"):
        validate_config({"extensions": ["bold", "bogus"]})


def test_undo_extension_keeps_its_tiptap_2_name() -> None:
    # Tiptap 3 renamed the extension undoRedo, but config.extensions names
    # built-ins by the vocabulary key, which stayed "history": a config written
    # for 0.10 keeps validating, and the new name is not a second spelling.
    assert validate_config({"extensions": ["history"]})
    with pytest.raises(ImproperlyConfigured, match="Unknown TipTap extension"):
        validate_config({"extensions": ["undoRedo"]})


@override_settings(TIPTAP_EXTRA_EXTENSIONS=["myExt"])
def test_extra_extension_is_allowed() -> None:
    assert validate_config({"extensions": ["bold", "myExt"]})


@pytest.mark.parametrize("mode", ["paragraph", "hardBreak", "swap"])
def test_valid_enter_key_passes(mode: str) -> None:
    assert validate_config({"enterKey": mode}) == {"enterKey": mode}


def test_invalid_enter_key_raises() -> None:
    with pytest.raises(ImproperlyConfigured, match="Invalid TipTap enterKey"):
        validate_config({"enterKey": "newline"})


# Keys validated as "a list of strings": font stacks/sizes and color swatches.
STRING_LIST_KEYS = ["fontFamilies", "fontSizes", "textColors", "highlightColors"]


@pytest.mark.parametrize("key", STRING_LIST_KEYS)
def test_string_list_of_strings_passes(key: str) -> None:
    cfg = {key: ["Arial, sans-serif", "#ff0000"]}
    assert validate_config(cfg) is cfg


@pytest.mark.parametrize("key", STRING_LIST_KEYS)
def test_empty_string_list_passes(key: str) -> None:
    assert validate_config({key: []}) == {key: []}


@pytest.mark.parametrize("key", STRING_LIST_KEYS)
def test_string_list_not_a_list_raises(key: str) -> None:
    with pytest.raises(ImproperlyConfigured, match=f"TipTap {key} must be a list of strings"):
        validate_config({key: "16px"})


@pytest.mark.parametrize("key", STRING_LIST_KEYS)
def test_string_list_with_non_string_item_raises(key: str) -> None:
    with pytest.raises(ImproperlyConfigured, match=f"TipTap {key} must be a list of strings"):
        validate_config({key: ["16px", 12]})


BOOL_KEYS = ["colorPicker", "imageResize"]


@pytest.mark.parametrize("key", BOOL_KEYS)
@pytest.mark.parametrize("value", [True, False])
def test_boolean_key_passes(key: str, value: bool) -> None:
    cfg = {key: value}
    assert validate_config(cfg) is cfg


def test_boolean_keys_omitted_pass() -> None:
    assert validate_config({}) == {}


@pytest.mark.parametrize("key", BOOL_KEYS)
@pytest.mark.parametrize("value", ["true", 1, ["#ff0000"]])
def test_boolean_key_non_boolean_raises(key: str, value: object) -> None:
    with pytest.raises(ImproperlyConfigured, match=f"TipTap {key} must be a boolean"):
        validate_config({key: value})


# ``features``: a list of built-in extension names restricting what one field's
# editor can do. Custom extensions are not features; they stay in ``extensions``.


@pytest.mark.parametrize("features", [[], ["bold"], ["heading", "table", "link"], ["bold", "bold"]])
def test_a_list_of_built_in_feature_names_passes(features: list[str]) -> None:
    cfg = {"features": features}
    assert validate_config(cfg) is cfg


def test_a_core_name_in_features_is_accepted() -> None:
    # Core is always on, so naming it is redundant rather than wrong.
    cfg = {"features": ["paragraph", "hardBreak", "history"]}
    assert validate_config(cfg) is cfg


def test_features_none_passes_as_omitted() -> None:
    assert validate_config({"features": None}) == {"features": None}


@pytest.mark.parametrize("value", ["heading", ("heading",), {"heading": True}])
def test_features_not_a_list_raises(value: object) -> None:
    # A bare string would otherwise pass the per-member check character by
    # character; this is the test holding the ``isinstance(value, list)`` conjunct.
    with pytest.raises(ImproperlyConfigured, match="TipTap features must be a list of strings"):
        validate_config({"features": value})


@pytest.mark.parametrize("member", [12, None, ["heading"]])
def test_features_with_a_non_string_member_raises(member: object) -> None:
    # ``["heading"]`` is unhashable: without the string check first, the name
    # lookup would raise TypeError rather than ImproperlyConfigured. This is the
    # test holding the per-member ``isinstance(item, str)`` conjunct.
    with pytest.raises(ImproperlyConfigured, match="TipTap features must be a list of strings"):
        validate_config({"features": ["bold", member]})


def test_an_unknown_feature_name_raises_naming_it_and_the_allowed_set() -> None:
    with pytest.raises(ImproperlyConfigured) as excinfo:
        validate_config({"features": ["bold", "headings", "tables"]})
    message = str(excinfo.value)
    assert "Unknown TipTap feature(s): ['headings', 'tables']" in message
    assert "'heading'" in message
    assert "'table'" in message
    # Assert which check answered: not the list-of-strings one.
    assert "must be a list of strings" not in message


@override_settings(TIPTAP_EXTRA_EXTENSIONS=["callout"])
def test_a_custom_extension_is_not_a_feature() -> None:
    with pytest.raises(ImproperlyConfigured, match=r"Unknown TipTap feature\(s\): \['callout'\]"):
        validate_config({"features": ["callout"], "extensions": ["callout"]})
