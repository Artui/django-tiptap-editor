from __future__ import annotations

import re

_NAME = r"""(?:"[^"\;<>\r\n]+"|'[^'\;<>\r\n]+'|[-\w]+(?:[ \t]+[-\w]+)*)"""  # quoted, or bare words
_FONT_FAMILY_RE = re.compile(rf"^{_NAME}(?:[ \t]*,[ \t]*{_NAME})*$")


def get_font_family(value: object) -> str:
    """Return a font-family list as written if every item is a safe name, else ``""``."""
    if not isinstance(value, str):
        return ""
    token = value.strip(" \t")
    return token if _FONT_FAMILY_RE.match(token) else ""
