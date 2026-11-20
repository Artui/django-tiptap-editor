from __future__ import annotations

import re

_NAME = (
    r"""(?:"[^"\\;<>\r\n]+"|'[^'\\;<>\r\n]+'|[-\w]+(?:[ \t]+[-\w]+)*)"""  # quoted, or bare words
)
_WS = r"[ \t\r\n\f]*"
_LIST = rf"{_NAME}(?:{_WS},{_WS}{_NAME})*"
_ITEM = rf"(?:{_NAME}|var\(--[-\w]+(?:{_WS},{_WS}{_LIST}{_WS})?\))"
_FONT_FAMILY_RE = re.compile(rf"^{_ITEM}(?:{_WS},{_WS}{_ITEM})*$")


def get_font_family(value: object) -> str:
    """Return a font-family list as written if every item is a safe name, else ``""``."""
    if not isinstance(value, str):
        return ""
    token = value.strip(" \t\r\n\f")
    return token if _FONT_FAMILY_RE.match(token) else ""
