from __future__ import annotations

import json
from typing import Any

from django import forms
from django.core.exceptions import ValidationError

from django_tiptap_editor.constants import STORAGE_FORMAT_JSON
from django_tiptap_editor.types.tiptap_value import TipTapValue
from django_tiptap_editor.utils.get_html_schema import get_html_schema
from django_tiptap_editor.utils.narrow_doc import narrow_doc
from django_tiptap_editor.utils.render_doc import render_doc
from django_tiptap_editor.utils.sanitize_doc import sanitize_doc
from django_tiptap_editor.utils.sanitize_html import sanitize_html
from django_tiptap_editor.utils.validate_json_depth import validate_json_depth
from django_tiptap_editor.widgets.tiptap_widget import TipTapWidget

_INVALID = "Enter a valid TipTap document (JSON)."


class TipTapJSONFormField(forms.Field):
    """Round-trips a TipTap editor's ``{doc, html}`` JSON envelope."""

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
        # A syntax error is not all ``json.loads`` raises on a body the client wrote: nesting deeper than the decoder recurses is a RecursionError (about a thousand levels on Python 3.10, so a 2 KB POST), and an integer longer than the interpreter converts is a ValueError, which JSONDecodeError subclasses.
        except (TypeError, ValueError, RecursionError) as exc:
            raise ValidationError(_INVALID) from exc
        try:
            parsed = TipTapValue.from_stored(data)
        except ValidationError as exc:
            raise ValidationError(_INVALID) from exc
        validate_json_depth(parsed.doc)
        config = self.widget.get_config({}) if isinstance(self.widget, TipTapWidget) else None
        sanitized = sanitize_doc(parsed.doc)
        doc = narrow_doc(sanitized, config=config)
        html = (
            render_doc(doc)
            if sanitized.get("content")
            else sanitize_html(parsed.html, schema=get_html_schema(config))
        )
        return TipTapValue(doc=doc, html=html)
