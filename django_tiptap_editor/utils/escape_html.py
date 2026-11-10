from __future__ import annotations


def escape_html(value: str, *, quote: bool = False) -> str:
    """Escape ``value`` for HTML text, or for a double-quoted attribute value."""
    escaped = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return escaped.replace('"', "&quot;") if quote else escaped
