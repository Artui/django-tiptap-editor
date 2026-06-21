"""The Python value of a JSON-stored TipTap field: canonical doc + HTML mirror."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.utils.safestring import SafeString, mark_safe


@dataclass(frozen=True)
class TipTapValue:
    """A JSON-stored editor value: the ProseMirror ``doc`` plus an HTML mirror.

    ``doc`` is the canonical, lossless representation (use it for programmatic
    work). ``html`` is the editor-derived rendering, marked safe so templates can
    render it directly: ``{{ obj.body }}`` or ``{{ obj.body.html }}`` — no
    ``|safe`` needed (the trust model matches HTML-mode storage; see the security
    docs). Mutating ``doc`` out of band leaves ``html`` stale until re-rendered.
    """

    doc: dict[str, Any]
    html: SafeString

    @classmethod
    def from_stored(cls, data: Any) -> TipTapValue:
        """Build a value from a stored mapping: a ``{doc, html}`` envelope or a
        bare ProseMirror doc (``{"type": "doc", …}``, no mirror yet)."""
        if not isinstance(data, dict):
            return cls(doc={}, html=mark_safe(""))
        if "doc" in data or "html" in data:
            doc = data.get("doc") or {}
            html = data.get("html") or ""
        else:
            doc, html = data, ""
        return cls(doc=doc if isinstance(doc, dict) else {}, html=mark_safe(str(html)))

    def to_stored(self) -> dict[str, Any]:
        """Return the plain ``{doc, html}`` mapping persisted in the JSON column."""
        return {"doc": self.doc, "html": str(self.html)}

    def __str__(self) -> str:
        return self.html

    def __html__(self) -> str:
        # Django templates treat objects with __html__ as already-safe.
        return self.html
