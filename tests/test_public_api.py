from __future__ import annotations

import django_tiptap_editor
from django_tiptap_editor.apps import DjangoTipTapEditorConfig


def test_public_api_reexports() -> None:
    assert django_tiptap_editor.TipTapWidget is not None
    assert django_tiptap_editor.AdminTipTapWidget is not None
    assert django_tiptap_editor.TipTapModelAdminMixin is not None
    assert django_tiptap_editor.TipTapFormField is not None
    assert django_tiptap_editor.TipTapJSONField is not None
    assert django_tiptap_editor.TipTapJSONFormField is not None
    assert django_tiptap_editor.TipTapValue is not None
    assert callable(django_tiptap_editor.get_default_config)
    assert callable(django_tiptap_editor.validate_config)


def test_app_config() -> None:
    assert DjangoTipTapEditorConfig.name == "django_tiptap_editor"
