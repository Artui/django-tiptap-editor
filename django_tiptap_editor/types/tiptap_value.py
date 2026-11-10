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
    """A JSON-stored editor value: the ProseMirror ``doc`` plus an HTML mirror."""

    doc: dict[str, Any]
    html: SafeString

    def __post_init__(self) -> None:
        # Local import: ``utils`` needs ``HtmlSchema`` from here; module scope makes them cycle.
        from django_tiptap_editor.utils.sanitize_html import sanitize_html

        if not isinstance(self.doc, dict):
            raise ValidationError(_NOT_A_DOCUMENT.format(value=self.doc))
        object.__setattr__(self, "html", sanitize_html(self.html))

    @classmethod
    def from_stored(cls, data: Any) -> TipTapValue:
        """Build a value from a stored ``{doc, html}`` envelope or a bare doc (no mirror yet)."""
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
        return {"doc": self.doc, "html": str.__str__(self.html)}

    def __str__(self) -> str:
        return self.html

    def __html__(self) -> str:
        # Django templates treat objects with __html__ as already-safe.
        return self.html
