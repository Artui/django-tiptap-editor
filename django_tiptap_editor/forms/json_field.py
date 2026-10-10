"""Form field for JSON-stored TipTap content (a ``{doc, html}`` envelope)."""

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
    """Round-trips a TipTap editor's ``{doc, html}`` JSON envelope.

    The widget is a ``TipTapWidget`` in JSON storage mode: the glue serializes
    ``{doc: editor.getJSON(), html: editor.getHTML()}`` into the textarea. This
    field renders a ``TipTapValue`` (or mapping) back to that JSON string and
    parses the submitted string into a ``TipTapValue``. Based on ``forms.Field``
    (not ``CharField``) because the cleaned value is a ``TipTapValue``, not a str.

    Cleaning is a validation step, not a transcription: a payload that is not a
    ``{doc, html}`` envelope or a bare doc is a field error rather than an empty
    document, the ``doc`` is protocol-allowlisted and narrowed to the features of
    the widget's config (``narrow_doc``), and the mirror is re-derived from it —
    so ``cleaned_data`` already holds what the model field would store, and a
    form used without a model is as safe to render as one with one.
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
        # A syntax error is not all ``json.loads`` raises on a body the client
        # wrote: nesting deeper than the decoder recurses is a RecursionError
        # (about a thousand levels on Python 3.10, so a 2 KB POST), and an
        # integer longer than the interpreter converts is a ValueError, which
        # JSONDecodeError subclasses. Either escaped as a 500.
        except (TypeError, ValueError, RecursionError) as exc:
            raise ValidationError(_INVALID) from exc
        try:
            parsed = TipTapValue.from_stored(data)
        except ValidationError as exc:
            raise ValidationError(_INVALID) from exc
        # Before anything re-encodes it: a ModelForm's model field runs json.dumps
        # in validate, which recurses per level and has no answer for a value
        # nested a few hundred levels inside ``attrs`` but a RecursionError.
        validate_json_depth(parsed.doc)
        # Narrowed to this field's features in the document itself: the model
        # field re-derives the mirror from the document on every save, with no
        # idea which form wrote it, so a mirror narrowed on its own would be
        # rendered back to the full document there.
        config = self.widget.get_config({}) if isinstance(self.widget, TipTapWidget) else None
        sanitized = sanitize_doc(parsed.doc)
        doc = narrow_doc(sanitized, config=config)
        # Re-derive the mirror from the sanitized doc, as the model field does
        # on save, so the cleaned value matches what will be stored rather than
        # what the client claimed. A doc with no content is the one case where
        # the mirror is the only copy of the content (a row seeded with legacy
        # HTML and not yet re-edited), so that mirror is kept instead of being
        # replaced by an empty rendering — sanitized against this field's own
        # allowlist, never as submitted, because nothing downstream narrows it.
        # Whether the doc had content is asked of it as submitted, not narrowed:
        # a lone rule on a field without rules narrows to nothing, and deciding
        # on that would store the caller's HTML as the mirror of a document that
        # never held it ("a document narrowed to nothing renders its own
        # mirror" in tests/forms/test_json_field.py).
        html = (
            render_doc(doc)
            if sanitized.get("content")
            else sanitize_html(parsed.html, schema=get_html_schema(config))
        )
        return TipTapValue(doc=doc, html=html)
