from __future__ import annotations

import json
from typing import Any

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from django_tiptap_editor.constants import (
    BUNDLE_CSS,
    BUNDLE_JS,
    CONFIG_ATTR,
    FEATURE_CORE,
    STORAGE_ATTR,
)
from django_tiptap_editor.widgets.admin_tiptap import AdminTipTapWidget
from django_tiptap_editor.widgets.tiptap_widget import TipTapWidget


def test_init_defaults_to_empty_config() -> None:
    assert TipTapWidget().config == {}


def test_init_keeps_config() -> None:
    assert TipTapWidget(config={"height": "300px"}).config == {"height": "300px"}


@override_settings(TIPTAP_DEFAULT_CONFIG={"locale": "sv"})
def test_get_config_merges_default_then_instance() -> None:
    widget = TipTapWidget(config={"height": "300px"})
    assert widget.get_config({}) == {"locale": "sv", "height": "300px"}


def test_get_context_injects_config_attr() -> None:
    widget = TipTapWidget(config={"height": "300px"})
    context = widget.get_context("body", "<p>x</p>", {})
    raw = context["widget"]["attrs"][CONFIG_ATTR]
    assert json.loads(raw) == {"height": "300px"}


def test_storage_attr_defaults_to_html() -> None:
    context = TipTapWidget().get_context("body", "", {})
    assert context["widget"]["attrs"][STORAGE_ATTR] == "html"


def test_storage_attr_honours_explicit_json() -> None:
    context = TipTapWidget(storage="json").get_context("body", "", {})
    assert context["widget"]["attrs"][STORAGE_ATTR] == "json"


@override_settings(TIPTAP_STORAGE_FORMAT="json")
def test_storage_attr_falls_back_to_setting() -> None:
    context = TipTapWidget().get_context("body", "", {})
    assert context["widget"]["attrs"][STORAGE_ATTR] == "json"


def test_media_emits_bundle() -> None:
    media = TipTapWidget().media
    assert BUNDLE_JS in media._js
    assert BUNDLE_CSS in media._css["all"]


def test_a_per_instance_config_beats_a_subclass_default() -> None:
    # The precedence the base docstring used to claim (subclass overrides last)
    # is the opposite of what the only shipped subclass does.
    assert AdminTipTapWidget(config={"height": "300px"}).get_config({})["height"] == "300px"


def _emitted(widget: TipTapWidget) -> dict[str, object]:
    """Return the config the browser reads, decoded from the rendered attribute."""
    return json.loads(widget.get_context("body", "", {})["widget"]["attrs"][CONFIG_ATTR])


def test_features_are_emitted_resolved_and_sorted() -> None:
    emitted = _emitted(TipTapWidget(config={"features": ["table", "bold"]}))
    features = emitted["features"]
    assert features == sorted(features)
    assert set(features) == (
        FEATURE_CORE | {"bold", "table", "tableRow", "tableCell", "tableHeader"}
    )


def test_emitted_features_carry_core_even_when_the_list_is_empty() -> None:
    assert _emitted(TipTapWidget(config={"features": []}))["features"] == sorted(FEATURE_CORE)


def test_emitted_features_close_over_chained_dependencies() -> None:
    # highlight -> backgroundColor -> textStyle: the browser receives all three,
    # so it needs no closure of its own on the Django path.
    features = _emitted(TipTapWidget(config={"features": ["highlight", "bulletList"]}))["features"]
    assert {"highlight", "backgroundColor", "textStyle", "bulletList", "listItem"} <= set(features)
    assert "heading" not in features


def test_emitted_features_are_deduplicated() -> None:
    features = _emitted(TipTapWidget(config={"features": ["bold", "bold", "paragraph"]}))[
        "features"
    ]
    assert features == sorted(FEATURE_CORE | {"bold"})


def test_no_features_key_leaves_the_emitted_config_untouched() -> None:
    # Omitting the key is the unrestricted editor, byte for byte as before.
    widget = TipTapWidget(config={"height": "300px"})
    assert widget.get_context("body", "", {})["widget"]["attrs"][CONFIG_ATTR] == json.dumps(
        {"height": "300px"}
    )


@override_settings(TIPTAP_DEFAULT_CONFIG={"features": ["bold"]})
def test_a_per_instance_none_lifts_a_project_wide_restriction() -> None:
    # ``None`` reads as omitted, so it is how one field opts back into the full
    # editor; the key is dropped rather than sent as ``null``.
    emitted = _emitted(TipTapWidget(config={"features": None, "height": "300px"}))
    assert emitted == {"height": "300px"}


@override_settings(TIPTAP_DEFAULT_CONFIG={"features": ["bold"], "locale": "sv"})
def test_a_project_wide_features_default_is_resolved() -> None:
    emitted = _emitted(TipTapWidget())
    assert emitted["features"] == sorted(FEATURE_CORE | {"bold"})
    assert emitted["locale"] == "sv"


@override_settings(TIPTAP_DEFAULT_CONFIG={"features": ["bold"]})
def test_a_per_instance_features_list_beats_the_project_default() -> None:
    emitted = _emitted(TipTapWidget(config={"features": ["italic"]}))
    assert emitted["features"] == sorted(FEATURE_CORE | {"italic"})


def test_an_invalid_features_list_fails_at_render() -> None:
    with pytest.raises(ImproperlyConfigured, match="Unknown TipTap feature"):
        TipTapWidget(config={"features": ["headings"]}).get_context("body", "", {})


def test_resolving_features_mutates_neither_the_instance_nor_the_setting() -> None:
    instance_features = ["table"]
    default_features = ["bold"]
    instance_config = {"features": instance_features}
    default_config = {"features": default_features}
    with override_settings(TIPTAP_DEFAULT_CONFIG=default_config):
        widget = TipTapWidget(config=instance_config)
        _emitted(widget)
        _emitted(TipTapWidget())
    assert widget.config is instance_config
    assert instance_config == {"features": instance_features}
    assert instance_config["features"] is instance_features
    assert instance_features == ["table"]
    assert default_config == {"features": default_features}
    assert default_config["features"] is default_features
    assert default_features == ["bold"]


def test_a_subclass_overriding_get_config_still_has_its_features_resolved() -> None:
    # Resolution happens where the config is written, not in ``get_config``,
    # which ``docs/api.md`` names as the override point.
    class Fixed(TipTapWidget):
        def get_config(self, attrs: dict[str, Any]) -> dict[str, Any]:
            return {"features": ["orderedList"]}

    assert _emitted(Fixed())["features"] == sorted(FEATURE_CORE | {"orderedList", "listItem"})


def test_the_base_docstring_does_not_claim_subclass_overrides_win() -> None:
    # A docs-drift guard, not a behaviour test: the sentence was wrong for every
    # subclass in the package, and prose is where a reader takes the rule from.
    assert "subclass overrides" not in (TipTapWidget.__doc__ or "")
