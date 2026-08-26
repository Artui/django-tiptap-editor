"""Form field for JSON-stored TipTap content (a ``{doc, html}`` envelope)."""

from __future__ import annotations

import json
from typing import Any

from django import forms
from django.core.exceptions import ValidationError
from django.utils.safestring import SafeString

from django_tiptap_editor.constants import STORAGE_FORMAT_JSON
from django_tiptap_editor.types.tiptap_value import TipTapValue
from django_tiptap_editor.utils.render_doc import render_doc
from django_tiptap_editor.utils.sanitize_doc import sanitize_doc
from django_tiptap_editor.widgets.tiptap_widget import TipTapWidget

_INVALID = "Enter a valid TipTap document (JSON)."


class TipTapJSONFormField(forms.Field):
    """Round-trips a TipTap editor's ``{doc, html}`` JSON envelope.

    The widget is a ``TipTapWidget`` in JSON storage mode: the glue serializes
    ``{doc: editor.getJSON(), html: editor.getHTML()}`` into the textarea. This
    field renders a ``TipTapValue`` (or mapping) back to that JSON string and
    parses the submitted string into a ``TipTapValue``. Based on ``forms.Field``
    (not ``CharField``) because the cleaned value is a ``TipTapValue``, not a str.

    Cleaning is a validation step, not a transcription: a payload that is not a
    ``{doc, html}`` envelope or a bare doc is a field error rather than an empty
    document, the ``doc`` is protocol-allowlisted, and the mirror is re-derived
    from it — so ``cleaned_data`` already holds what the model field would store,
    and a form used without a model is as safe to render as one with one.
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
            raise ValidationError(_INVALID) from exc
        try:
            parsed = TipTapValue.from_stored(data)
        except ValidationError as exc:
            raise ValidationError(_INVALID) from exc
        doc = sanitize_doc(parsed.doc)
        # Re-derive the mirror from the sanitized doc, as the model field does
        # on save, so the cleaned value matches what will be stored rather than
        # what the client claimed. A doc with no content is the one case where
        # the mirror is the only copy of the content (a row seeded with legacy
        # HTML and not yet re-edited), so that mirror is kept instead of being
        # replaced by an empty rendering — sanitized, never as submitted.
        html = render_doc(doc) if doc.get("content") else SafeString(parsed.html)
        return TipTapValue(doc=doc, html=html)
