from __future__ import annotations

from django_tiptap_editor.widgets.admin_tiptap import AdminTipTapWidget


def test_admin_default_height_applied() -> None:
    assert AdminTipTapWidget().get_config({}) == {"height": "500px"}


def test_instance_config_overrides_admin_default() -> None:
    widget = AdminTipTapWidget(config={"height": "700px"})
    assert widget.get_config({}) == {"height": "700px"}
