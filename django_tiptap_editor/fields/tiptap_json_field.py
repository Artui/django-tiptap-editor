from __future__ import annotations

import json
from typing import Any

from django.core.exceptions import ValidationError
from django.db import models

from django_tiptap_editor.constants import DEFAULT_IMAGE_PROTOCOLS, DEFAULT_LINK_PROTOCOLS
from django_tiptap_editor.forms.json_field import TipTapJSONFormField
from django_tiptap_editor.types.tiptap_value import TipTapValue
from django_tiptap_editor.utils.get_extra_attributes import get_extra_attributes
from django_tiptap_editor.utils.get_extra_extensions import get_extra_extensions
from django_tiptap_editor.utils.render_doc import render_doc
from django_tiptap_editor.utils.sanitize_doc import sanitize_doc
from django_tiptap_editor.utils.validate_json_depth import validate_json_depth

# The node and mark vocabulary the server-side renderer can express. Kept in
# sync with render_doc's dispatch chain: a type outside it is flattened to its
# text content when the HTML mirror is derived, so the wrapper (and its attrs)
# would vanish from the mirror on the first save. Validation rejects such a
# document instead of storing one the mirror cannot represent; a project whose
# custom extensions add types declares them in TIPTAP_EXTRA_EXTENSIONS.
_RENDERABLE_NODE_TYPES = frozenset(
    {
        "blockquote",
        "bulletList",
        "codeBlock",
        "doc",
        "hardBreak",
        "heading",
        "horizontalRule",
        "image",
        "listItem",
        "orderedList",
        "paragraph",
        "table",
        "tableCell",
        "tableHeader",
        "tableRow",
        "text",
    }
)
_RENDERABLE_MARK_TYPES = frozenset(
    {
        "bold",
        "code",
        "italic",
        "link",
        "strike",
        "subscript",
        "superscript",
        "textStyle",
        "underline",
    }
)


def _unknown_types(doc: Any, node_types: frozenset[str], mark_types: frozenset[str]) -> set[str]:
    """Return the ``type`` names in ``doc`` outside the given vocabularies."""
    unknown: set[str] = set()
    stack: list[tuple[Any, frozenset[str]]] = [(doc, node_types)]
    while stack:
        item, allowed = stack.pop()
        if not isinstance(item, dict):
            continue
        kind = item.get("type")
        if isinstance(kind, str) and kind not in allowed:
            unknown.add(kind)
        marks = item.get("marks")
        if isinstance(marks, list):
            stack.extend((mark, mark_types) for mark in marks)
        content = item.get("content")
        if isinstance(content, list):
            stack.extend((child, node_types) for child in content)
    return unknown


class TipTapJSONField(models.JSONField):
    """A ``JSONField`` storing ``{doc, html}`` and exposing a ``TipTapValue``."""

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
            # ``JSONField`` has no ``to_python``, so ``super()`` returns the string unparsed.
            try:
                value = json.loads(value)
            except (ValueError, RecursionError) as exc:
                raise ValidationError(
                    "Value must be valid JSON.", code="invalid", params={"value": value}
                ) from exc
        return TipTapValue.from_stored(value)

    def validate(self, value: Any, model_instance: Any) -> None:
        """Validate a ``TipTapValue`` the way ``JSONField`` validates a mapping."""
        if value is None:
            super().validate(value, model_instance)
            return
        coerced = value if isinstance(value, TipTapValue) else TipTapValue.from_stored(value)
        validate_json_depth(coerced.doc)
        super().validate(coerced.to_stored(), model_instance)
        extras = set(get_extra_extensions())
        unknown = _unknown_types(
            coerced.doc, _RENDERABLE_NODE_TYPES | extras, _RENDERABLE_MARK_TYPES | extras
        )
        if unknown:
            raise ValidationError(
                "Unknown TipTap node or mark type(s): %(types)s. The server-side "
                "HTML mirror cannot render them, so they would be dropped from it. "
                "List them in TIPTAP_EXTRA_EXTENSIONS if the project renders the "
                "document itself.",
                code="unknown_type",
                params={"types": ", ".join(sorted(unknown))},
            )

    def get_prep_value(self, value: Any) -> Any:
        if value is None:
            return super().get_prep_value(None)
        coerced = value if isinstance(value, TipTapValue) else TipTapValue.from_stored(value)
        # Saving is the other ``json.dumps``, and ``save()`` runs no ``validate``.
        validate_json_depth(coerced.doc)
        doc = sanitize_doc(
            coerced.doc,
            link_protocols=self.link_protocols,
            image_protocols=self.image_protocols,
        )
        html = (
            render_doc(
                doc,
                link_protocols=self.link_protocols,
                image_protocols=self.image_protocols,
                extra_attributes=get_extra_attributes(),
            )
            if doc.get("content")
            else coerced.html
        )
        clean = TipTapValue(doc=doc, html=html)
        return super().get_prep_value(clean.to_stored())

    def value_to_string(self, obj: Any) -> Any:
        """The stored ``{doc, html}`` mapping, for the serialization framework."""
        value = self.value_from_object(obj)
        return value.to_stored() if isinstance(value, TipTapValue) else value

    def formfield(self, **kwargs: Any) -> Any:
        kwargs.setdefault("form_class", TipTapJSONFormField)
        # Skip ``JSONField.formfield`` (it forces ``forms.JSONField``) for our CharField form.
        return models.Field.formfield(self, **kwargs)
