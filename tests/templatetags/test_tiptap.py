from __future__ import annotations

import json

from django.template import Context, Template
from django.test import override_settings

from django_tiptap_editor.templatetags.tiptap import tiptap_config, tiptap_html, tiptap_media
from django_tiptap_editor.types.tiptap_value import TipTapValue


def test_media_bundle_mode() -> None:
    html = tiptap_media()
    assert "tiptap.bundle.js" in html
    assert "tiptap.bundle.css" in html
    assert "importmap" not in html


@override_settings(
    TIPTAP_ASSET_MODE="external",
    TIPTAP_IMPORT_MAP={"@tiptap/core": "https://esm.sh/@tiptap/core"},
)
def test_media_external_mode() -> None:
    html = tiptap_media()
    assert "importmap" in html
    assert 'type="module"' in html
    assert "tiptap.glue.esm.js" in html
    assert "https://esm.sh/@tiptap/core" in html


@override_settings(TIPTAP_DEFAULT_CONFIG={"locale": "sv"})
def test_config_outputs_json() -> None:
    assert json.loads(tiptap_config()) == {"locale": "sv"}


def test_tiptap_html_filter_uses_value_mirror() -> None:
    value = TipTapValue.from_stored({"doc": {}, "html": "<p>mirror</p>"})
    assert tiptap_html(value) == "<p>mirror</p>"


def test_tiptap_html_filter_renders_bare_doc() -> None:
    doc = {
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": "x"}]}],
    }
    assert tiptap_html(doc) == "<p>x</p>"


def test_tiptap_html_filter_sanitizes_a_stored_html_string() -> None:
    # HTML storage: the column holds a plain str, and content stored before the
    # field sanitized it is only made safe here.
    assert tiptap_html("<img src=x onerror=alert(1)>") == '<img src="x">'


def test_tiptap_html_filter_keeps_editor_markup_intact() -> None:
    markup = '<p style="text-align: center;">hi <strong>there</strong></p>'
    assert tiptap_html(markup) == markup


def test_tiptap_html_filter_renders_a_safe_value_mirror() -> None:
    value = TipTapValue.from_stored({"doc": {}, "html": "<img src=x onerror=alert(1)>"})
    assert tiptap_html(value) == '<img src="x">'


def test_tiptap_html_filter_output_is_safe_in_a_template() -> None:
    rendered = Template("{% load tiptap %}{{ v|tiptap_html }}").render(
        Context({"v": "<p>a &amp; b</p>"})
    )
    assert rendered == "<p>a &amp; b</p>"
