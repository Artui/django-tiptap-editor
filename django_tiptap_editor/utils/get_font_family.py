from __future__ import annotations

import re

_NAME = (
    r"""(?:"[^"\\;<>\r\n]+"|'[^'\\;<>\r\n]+'|[-\w]+(?:[ \t]+[-\w]+)*)"""  # quoted, or bare words
)
_LIST = rf"{_NAME}(?:\s*,\s*{_NAME})*"
_ITEM = rf"(?:{_NAME}|var\(--[-\w]+(?:\s*,\s*{_LIST}\s*)?\))"
_FONT_FAMILY_RE = re.compile(rf"^{_ITEM}(?:\s*,\s*{_ITEM})*$")


def get_font_family(value: object) -> str:
    """Return a font-family list as written if every item is a safe name, else ``""``."""
    if not isinstance(value, str):
        return ""
    token = value.strip()
    return token if _FONT_FAMILY_RE.match(token) else ""
