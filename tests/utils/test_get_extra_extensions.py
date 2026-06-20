from __future__ import annotations

from django.test import override_settings

from django_tiptap_editor.utils.get_extra_extensions import get_extra_extensions


def test_default_is_empty() -> None:
    assert get_extra_extensions() == frozenset()


@override_settings(TIPTAP_EXTRA_EXTENSIONS=["myExt", "other"])
def test_returns_setting_as_set() -> None:
    assert get_extra_extensions() == frozenset({"myExt", "other"})
