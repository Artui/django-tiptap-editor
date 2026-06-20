from __future__ import annotations

from django.test import override_settings

from django_tiptap_editor.utils.get_default_config import get_default_config


def test_default_is_empty() -> None:
    assert get_default_config() == {}


@override_settings(TIPTAP_DEFAULT_CONFIG={"height": "550px"})
def test_merges_setting() -> None:
    assert get_default_config() == {"height": "550px"}
