from __future__ import annotations

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from django_tiptap_editor.get_asset_mode import get_asset_mode


def test_default_is_bundle() -> None:
    assert get_asset_mode() == "bundle"


@override_settings(TIPTAP_ASSET_MODE="external")
def test_external() -> None:
    assert get_asset_mode() == "external"


@override_settings(TIPTAP_ASSET_MODE="nope")
def test_invalid_raises() -> None:
    with pytest.raises(ImproperlyConfigured):
        get_asset_mode()
