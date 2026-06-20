from __future__ import annotations

import json

from django.test import override_settings

from django_tiptap_editor.templatetags.tiptap import tiptap_config, tiptap_media


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
