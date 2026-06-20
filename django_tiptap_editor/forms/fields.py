"""Optional form field defaulting to the TipTap widget."""

from __future__ import annotations

from django import forms

from django_tiptap_editor.widgets.tiptap_widget import TipTapWidget


class TipTapFormField(forms.CharField):
    """A ``CharField`` whose default widget is ``TipTapWidget``."""

    widget = TipTapWidget
