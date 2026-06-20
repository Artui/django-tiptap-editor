from __future__ import annotations

from django.test import override_settings

from django_tiptap_editor.constants import GLUE_IMPORT_SPECIFIERS, TIPTAP_VERSION
from django_tiptap_editor.utils.get_import_map import default_import_map, get_import_map


def test_default_pins_every_glue_specifier() -> None:
    mapping = get_import_map()
    assert set(mapping) == set(GLUE_IMPORT_SPECIFIERS)
    assert mapping["@tiptap/core"] == f"https://esm.sh/@tiptap/core@{TIPTAP_VERSION}"


def test_default_import_map_helper_matches() -> None:
    assert get_import_map() == default_import_map()


@override_settings(TIPTAP_IMPORT_MAP={"@tiptap/core": "https://cdn.example/core.js"})
def test_explicit_setting_overrides_default() -> None:
    assert get_import_map() == {"@tiptap/core": "https://cdn.example/core.js"}


@override_settings(TIPTAP_IMPORT_MAP={})
def test_explicit_empty_map_is_respected() -> None:
    assert get_import_map() == {}
