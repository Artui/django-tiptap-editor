from __future__ import annotations

from typing import Any

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from django_tiptap_editor.utils.get_extra_attributes import get_extra_attributes


def test_no_key_grants_nothing() -> None:
    assert get_extra_attributes({}) == {}


@override_settings(TIPTAP_DEFAULT_CONFIG={"extraAttributes": {"heading": ["class"]}})
def test_no_config_reads_the_project_default() -> None:
    assert get_extra_attributes() == {"heading": ("class",)}
    assert get_extra_attributes({"extraAttributes": {}}) == {}


def test_a_grant_is_deduplicated_and_an_empty_list_dropped() -> None:
    grant = {"paragraph": ["class", "class"], "heading": []}
    assert get_extra_attributes({"extraAttributes": grant}) == {"paragraph": ("class",)}


@pytest.mark.parametrize(
    ("grant", "message"),
    [
        (["class"], "must map a node type"),
        ({"blockquote": ["class"]}, "unsupported node type"),
        ({"paragraph": ["id"]}, "unsupported attribute"),
        ({"paragraph": ["data-x"]}, "unsupported attribute"),
        ({"paragraph": "class"}, "must be a list"),
        ({"paragraph": None}, "must be a list"),
    ],
)
def test_a_malformed_grant_is_refused(grant: Any, message: str) -> None:
    with pytest.raises(ImproperlyConfigured, match=message):
        get_extra_attributes({"extraAttributes": grant})
