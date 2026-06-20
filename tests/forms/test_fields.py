from __future__ import annotations

from django_tiptap_editor.forms.fields import TipTapFormField
from django_tiptap_editor.widgets.tiptap_widget import TipTapWidget


def test_default_widget_is_tiptap() -> None:
    assert isinstance(TipTapFormField().widget, TipTapWidget)
