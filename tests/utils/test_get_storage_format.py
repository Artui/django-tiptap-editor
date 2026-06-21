from __future__ import annotations

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from django_tiptap_editor.utils.get_storage_format import get_storage_format


def test_defaults_to_html() -> None:
    assert get_storage_format() == "html"


@override_settings(TIPTAP_STORAGE_FORMAT="json")
def test_reads_json_setting() -> None:
    assert get_storage_format() == "json"


@override_settings(TIPTAP_STORAGE_FORMAT="yaml")
def test_rejects_unknown_format() -> None:
    with pytest.raises(ImproperlyConfigured):
        get_storage_format()
