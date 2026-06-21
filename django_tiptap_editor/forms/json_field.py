"""Form field for JSON-stored TipTap content (a ``{doc, html}`` envelope)."""

from __future__ import annotations

import json
from typing import Any

from django import forms
from django.core.exceptions import ValidationError

from django_tiptap_editor.constants import STORAGE_FORMAT_JSON
from django_tiptap_editor.types.tiptap_value import TipTapValue
from django_tiptap_editor.widgets.tiptap_widget import TipTapWidget


class TipTapJSONFormField(forms.Field):
    """Round-trips a TipTap editor's ``{doc, html}`` JSON envelope.

    The widget is a ``TipTapWidget`` in JSON storage mode: the glue serializes
    ``{doc: editor.getJSON(), html: editor.getHTML()}`` into the textarea. This
    field renders a ``TipTapValue`` (or mapping) back to that JSON string and
    parses the submitted string into a ``TipTapValue``. Based on ``forms.Field``
    (not ``CharField``) because the cleaned value is a ``TipTapValue``, not a str.
    """

    widget = TipTapWidget

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("widget", TipTapWidget(storage=STORAGE_FORMAT_JSON))
        super().__init__(**kwargs)

    def prepare_value(self, value: Any) -> Any:
        if value is None:
            return ""
        if isinstance(value, TipTapValue):
            return json.dumps(value.to_stored())
        if isinstance(value, dict):
            return json.dumps(value)
        return value  # already the submitted/JSON string

    def to_python(self, value: Any) -> TipTapValue | None:
        if value in (None, ""):
            return None
        if isinstance(value, TipTapValue):
            return value
        try:
            data = json.loads(value)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValidationError("Enter a valid TipTap document (JSON).") from exc
        return TipTapValue.from_stored(data)
