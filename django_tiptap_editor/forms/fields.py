"""Optional form field defaulting to the TipTap widget."""

from __future__ import annotations

from typing import Any

from django import forms

from django_tiptap_editor.utils.sanitize_html import sanitize_html
from django_tiptap_editor.widgets.tiptap_widget import TipTapWidget


class TipTapFormField(forms.CharField):
    """A ``CharField`` whose default widget is ``TipTapWidget``.

    The cleaned value is the submitted markup put through ``sanitize_html``.
    The editor's own schema normalises content in the browser, which makes it a
    formatter rather than a boundary: the textarea is a plain form field, so a
    client that never loads the editor posts whatever it likes. Sanitising in
    ``to_python`` means the value the form hands back — and therefore the value a
    view saves — is already reduced to markup the editor could have produced,
    and length validation counts what will actually be stored.
    """

    widget = TipTapWidget

    def to_python(self, value: Any) -> Any:
        cleaned = sanitize_html(super().to_python(value))
        # Hand back a plain str rather than the sanitiser's SafeString. The value
        # is assigned to a text column and comes back from the database unmarked,
        # so keeping the marking here would make the same content render one way
        # in the request that saved it and another on the next page load. Display
        # goes through the ``tiptap_html`` filter, which marks it at that point.
        return cleaned + ""
