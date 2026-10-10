from __future__ import annotations

import json

from django.test import override_settings

from django_tiptap_editor.constants import CONFIG_ATTR, FEATURE_CORE
from django_tiptap_editor.widgets.admin_tiptap import AdminTipTapWidget


def test_admin_default_height_applied() -> None:
    assert AdminTipTapWidget().get_config({}) == {"height": "500px"}


def test_instance_config_overrides_admin_default() -> None:
    widget = AdminTipTapWidget(config={"height": "700px"})
    assert widget.get_config({}) == {"height": "700px"}


def _emitted(widget: AdminTipTapWidget) -> dict[str, object]:
    return json.loads(widget.get_context("body", "", {})["widget"]["attrs"][CONFIG_ATTR])


def test_admin_widget_emits_resolved_features() -> None:
    emitted = _emitted(AdminTipTapWidget(config={"features": ["bulletList"]}))
    assert emitted == {
        "height": "500px",
        "features": sorted(FEATURE_CORE | {"bulletList", "listItem"}),
    }


@override_settings(TIPTAP_DEFAULT_CONFIG={"features": ["bold"]})
def test_admin_widget_resolves_a_project_wide_features_default() -> None:
    assert _emitted(AdminTipTapWidget())["features"] == sorted(FEATURE_CORE | {"bold"})


@override_settings(TIPTAP_DEFAULT_CONFIG={"features": ["bold"]})
def test_admin_widget_per_instance_features_beat_the_project_default() -> None:
    emitted = _emitted(AdminTipTapWidget(config={"features": ["table"]}))
    assert emitted["features"] == sorted(
        FEATURE_CORE | {"table", "tableRow", "tableCell", "tableHeader"}
    )
    assert "bold" not in emitted["features"]
