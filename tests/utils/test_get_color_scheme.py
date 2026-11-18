from __future__ import annotations

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from django_tiptap_editor.utils.get_color_scheme import get_color_scheme


def test_unset_is_none() -> None:
    assert get_color_scheme() is None


@pytest.mark.parametrize("scheme", ["light", "dark", "system"])
def test_reads_each_scheme(scheme: str) -> None:
    with override_settings(TIPTAP_COLOR_SCHEME=scheme):
        assert get_color_scheme() == scheme


@pytest.mark.parametrize("scheme", ["auto", "page", "Dark", "", True])
def test_rejects_anything_else(scheme: object) -> None:
    with override_settings(TIPTAP_COLOR_SCHEME=scheme), pytest.raises(ImproperlyConfigured):
        get_color_scheme()
