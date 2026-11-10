from __future__ import annotations

from typing import Any

from django import forms

from django_tiptap_editor.utils.get_html_schema import get_html_schema
from django_tiptap_editor.utils.sanitize_html import sanitize_html
from django_tiptap_editor.widgets.tiptap_widget import TipTapWidget


class TipTapFormField(forms.CharField):
    """A ``CharField`` whose default widget is ``TipTapWidget``."""

    widget = TipTapWidget

    def to_python(self, value: Any) -> Any:
        value = super().to_python(value)
        # Empty input is ``empty_value`` (None when nullable): sanitising would store "", not NULL.
        if value in self.empty_values:
            return value
        config = self.widget.get_config({}) if isinstance(self.widget, TipTapWidget) else None
        cleaned = sanitize_html(value, schema=get_html_schema(config))
        return cleaned + ""
