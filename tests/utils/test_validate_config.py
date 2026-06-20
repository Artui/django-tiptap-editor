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


@override_settings(TIPTAP_EXTRA_EXTENSIONS=["myExt"])
def test_extra_extension_is_allowed() -> None:
    assert validate_config({"extensions": ["bold", "myExt"]})
