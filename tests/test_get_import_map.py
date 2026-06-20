from __future__ import annotations

from django.test import override_settings

from django_tiptap_editor.get_import_map import get_import_map


def test_default_is_empty() -> None:
    assert get_import_map() == {}


@override_settings(TIPTAP_IMPORT_MAP={"@tiptap/core": "https://esm.sh/@tiptap/core"})
def test_returns_setting() -> None:
    assert get_import_map() == {"@tiptap/core": "https://esm.sh/@tiptap/core"}
