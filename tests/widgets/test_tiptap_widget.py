from __future__ import annotations

import json

from django.test import override_settings

from django_tiptap_editor.constants import BUNDLE_CSS, BUNDLE_JS, CONFIG_ATTR, STORAGE_ATTR
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
