"""Model field storing TipTap content as a JSON ``{doc, html}`` envelope."""

from __future__ import annotations

from typing import Any

from django.db import models

from django_tiptap_editor.constants import DEFAULT_IMAGE_PROTOCOLS, DEFAULT_LINK_PROTOCOLS
from django_tiptap_editor.forms.json_field import TipTapJSONFormField
from django_tiptap_editor.types.tiptap_value import TipTapValue
from django_tiptap_editor.utils.render_doc import render_doc
from django_tiptap_editor.utils.sanitize_doc import sanitize_doc


class TipTapJSONField(models.JSONField):
    """A ``JSONField`` storing ``{doc, html}`` and exposing a ``TipTapValue``.

    The Python value on a model instance is a ``TipTapValue`` (``.doc`` is the
    canonical ProseMirror JSON; ``.html`` a safe, server-derived mirror). On save
    the ``doc`` is protocol-allowlisted (``sanitize_doc``) and the ``html`` mirror
    is re-derived from it (``render_doc``), so both the canonical value and the
    rendered surface are always safe regardless of who wrote them — any
    caller-supplied ``html`` is discarded. The default form field renders the
    editor in JSON storage mode.
    """

    def __init__(
        self,
        *args: Any,
        link_protocols: tuple[str, ...] = DEFAULT_LINK_PROTOCOLS,
        image_protocols: tuple[str, ...] = DEFAULT_IMAGE_PROTOCOLS,
        **kwargs: Any,
    ) -> None:
        self.link_protocols = link_protocols
        self.image_protocols = image_protocols
        super().__init__(*args, **kwargs)

    def from_db_value(self, value: Any, expression: Any, connection: Any) -> TipTapValue | None:
        parsed = super().from_db_value(value, expression, connection)
        if parsed is None:
            return None
        return TipTapValue.from_stored(parsed)

    def to_python(self, value: Any) -> TipTapValue | None:
        if value is None or isinstance(value, TipTapValue):
            return value
        if isinstance(value, str):
            value = super().to_python(value)
        return TipTapValue.from_stored(value)

    def get_prep_value(self, value: Any) -> Any:
        if value is None:
            return super().get_prep_value(None)
        coerced = value if isinstance(value, TipTapValue) else TipTapValue.from_stored(value)
        doc = sanitize_doc(
            coerced.doc,
            link_protocols=self.link_protocols,
            image_protocols=self.image_protocols,
        )
        # Always re-derive the HTML mirror from the sanitized doc — never trust a
        # caller-supplied `html`. A write can set `{doc, html}` directly (API /
        # import / hand-edit) with benign `doc` but hostile `html`; deriving the
        # mirror here guarantees the rendered surface only ever reflects the
        # sanitized doc. render_doc's output is protocol-allowlisted, HTML-escaped
        # and CSS-validated, so it is safe to mark for `|safe`.
        html = render_doc(
            doc, link_protocols=self.link_protocols, image_protocols=self.image_protocols
        )
        clean = TipTapValue(doc=doc, html=html)
        return super().get_prep_value(clean.to_stored())

    def formfield(self, **kwargs: Any) -> Any:
        kwargs.setdefault("form_class", TipTapJSONFormField)
        # Skip JSONField.formfield (which forces forms.JSONField) — go to the
        # generic field machinery so our CharField-based form class is used.
        return models.Field.formfield(self, **kwargs)
