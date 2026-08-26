"""Model field storing TipTap content as a JSON ``{doc, html}`` envelope."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import models

from django_tiptap_editor.constants import DEFAULT_IMAGE_PROTOCOLS, DEFAULT_LINK_PROTOCOLS
from django_tiptap_editor.forms.json_field import TipTapJSONFormField
from django_tiptap_editor.types.tiptap_value import TipTapValue
from django_tiptap_editor.utils.get_extra_extensions import get_extra_extensions
from django_tiptap_editor.utils.render_doc import render_doc
from django_tiptap_editor.utils.sanitize_doc import sanitize_doc

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
    """Return the ``type`` names in ``doc`` outside the given vocabularies.

    Iterative rather than recursive: a document deep enough to exhaust the
    interpreter's stack must fail validation, not raise ``RecursionError``.
    """
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
    """A ``JSONField`` storing ``{doc, html}`` and exposing a ``TipTapValue``.

    The Python value on a model instance is a ``TipTapValue`` (``.doc`` is the
    canonical ProseMirror JSON; ``.html`` a safe, server-derived mirror). On save
    the ``doc`` is protocol-allowlisted (``sanitize_doc``) and the ``html`` mirror
    is re-derived from it (``render_doc``), so both the canonical value and the
    rendered surface are always safe regardless of who wrote them — any
    caller-supplied ``html`` is discarded. The default form field renders the
    editor in JSON storage mode.

    Validation (``full_clean``, a ``ModelForm``, the admin) checks the stored
    mapping is JSON-serializable and that every node and mark type is one the
    HTML mirror can render — see ``TIPTAP_EXTRA_EXTENSIONS`` to declare the types
    a project's own extensions add.
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

    def validate(self, value: Any, model_instance: Any) -> None:
        """Validate a ``TipTapValue`` the way ``JSONField`` validates a mapping.

        ``JSONField.validate`` runs ``json.dumps`` over the value, which a
        ``TipTapValue`` dataclass is not — so every ``ModelForm``, ``full_clean``
        and admin save failed with "Value must be valid JSON" while the plain ORM
        path accepted the same value. The stored mapping is what actually reaches
        the column, so that is what gets checked. On top of the JSON check, the
        document's node and mark types must be ones the HTML mirror can render.
        """
        if value is None:
            super().validate(value, model_instance)
            return
        coerced = value if isinstance(value, TipTapValue) else TipTapValue.from_stored(value)
        super().validate(coerced.to_stored(), model_instance)
        extras = get_extra_extensions()
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
        doc = sanitize_doc(
            coerced.doc,
            link_protocols=self.link_protocols,
            image_protocols=self.image_protocols,
        )
        # Always re-derive the HTML mirror from the sanitized doc — never trust a
        # caller-supplied `html`. A write can set `{doc, html}` directly (API /
        # import / hand-edit) with a benign `doc` but a hostile `html`, so
        # deriving it here is what makes the rendered surface reflect only the
        # sanitized doc.
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
