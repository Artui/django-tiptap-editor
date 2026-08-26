"""The conservative CSS value gate shared by the renderer and the sanitiser."""

from __future__ import annotations

import re

# Word chars, spaces, and the punctuation real values use (#hex, %, commas, dots,
# parens for rgb(), hyphens). Rejects anything with ``;`` ``:`` ``{`` ``}`` ``<``
# ``>`` quotes -- i.e. property-injection, url(...:...) and markup -- so style
# attributes can't smuggle script.
_CSS_VALUE_RE = re.compile(r"^[#%(),.\-\s\w]+$")


def get_css_value(value: object) -> str:
    """Return a CSS value if it is a safe simple token, else ``""``."""
    if not isinstance(value, str):
        return ""
    token = value.strip()
    if not token or not _CSS_VALUE_RE.match(token) or "expression" in token.lower():
        return ""
    return token
