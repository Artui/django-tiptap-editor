"""The Python value of a JSON-stored TipTap field: canonical doc + HTML mirror."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.core.exceptions import ValidationError
from django.utils.safestring import SafeString

_NOT_A_DOCUMENT = (
    "A TipTap JSON value must be a {{'doc': ..., 'html': ...}} envelope or a bare "
    "ProseMirror doc mapping, got {value!r}. HTML is not converted on assignment: "
    "to move a column from HTML storage to JSON storage, parse each row into a "
    "ProseMirror doc first (the bundle's DjangoTipTap.htmlToStored does it in the "
    "browser), or store the markup as {{'doc': {{}}, 'html': '<p>...</p>'}}."
)


@dataclass(frozen=True)
class TipTapValue:
    """A JSON-stored editor value: the ProseMirror ``doc`` plus an HTML mirror.

    ``doc`` is the canonical, lossless representation (use it for programmatic
    work). ``html`` is a rendering of ``doc``, marked safe so templates can render
    it directly: ``{{ obj.body }}`` or ``{{ obj.body.html }}``, no ``|safe``
    needed. What makes that safe is an invariant this class enforces on every
    instance, however it was built: the mirror is put through ``sanitize_html``
    in ``__post_init__``, so no caller — a form, an import, a hand-written
    ``TipTapValue(...)`` — can hand a template markup the editor could not have
    produced. ``TipTapJSONField`` additionally re-derives the mirror from the
    sanitized ``doc`` on save. Mutating ``doc`` out of band leaves ``html`` stale
    until re-rendered.

    Raises ``ValidationError`` when ``doc`` is not a mapping, rather than
    substituting an empty document: silently emptying a document is the failure
    mode a rich-text field can least afford.
    """

    doc: dict[str, Any]
    html: SafeString

    def __post_init__(self) -> None:
        # Local import: the sanitiser resolves its allowlist through
        # ``utils.get_html_schema``, which needs ``HtmlSchema`` from this very
        # package — importing it at module scope makes ``types`` and ``utils``
        # import each other. The types package stays free of utils imports.
        from django_tiptap_editor.utils.sanitize_html import sanitize_html

        if not isinstance(self.doc, dict):
            raise ValidationError(_NOT_A_DOCUMENT.format(value=self.doc))
        object.__setattr__(self, "html", sanitize_html(self.html))

    @classmethod
    def from_stored(cls, data: Any) -> TipTapValue:
        """Build a value from a stored mapping: a ``{doc, html}`` envelope or a
        bare ProseMirror doc (``{"type": "doc", …}``, no mirror yet).

        Raises ``ValidationError`` for anything that is not one of those shapes.
        """
        if not isinstance(data, dict):
            raise ValidationError(_NOT_A_DOCUMENT.format(value=data))
        if "doc" in data or "html" in data:
            doc = data.get("doc") or {}
            html = data.get("html") or ""
        else:
            doc, html = data, ""
        if not isinstance(html, str):
            raise ValidationError(
                f"A TipTap JSON value's 'html' mirror must be a string, got {html!r}."
            )
        return cls(doc=doc, html=SafeString(html))

    def to_stored(self) -> dict[str, Any]:
        """Return the plain ``{doc, html}`` mapping persisted in the JSON column."""
        return {"doc": self.doc, "html": str(self.html)}

    def __str__(self) -> str:
        return self.html

    def __html__(self) -> str:
        # Django templates treat objects with __html__ as already-safe.
        return self.html
