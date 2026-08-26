"""Protocol allowlisting for a stored URL (internal helper)."""

from __future__ import annotations

import re

_SCHEME_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):")

# ASCII whitespace and C0/DEL control characters (``\x00``-``\x20`` and ``\x7f``).
# A browser strips these while resolving a URL -- tabs/newlines are removed from
# anywhere in the string, leading controls/spaces are trimmed -- so an attacker
# embeds them mid-scheme (``java\nscript:``) to hide a disallowed scheme from a
# naive parser. We remove them before scheme detection to see what the browser
# will.
_URL_STRIP_RE = re.compile(r"[\x00-\x20\x7f]")


def _scheme(url: object) -> str:
    """Return the lowercased URL scheme, or ``""`` for a relative/anchor URL."""
    if not isinstance(url, str):
        return ""
    match = _SCHEME_RE.match(_URL_STRIP_RE.sub("", url))
    return match.group(1).lower() if match else ""


def is_allowed_url(url: object, protocols: tuple[str, ...]) -> bool:
    """Return whether ``url``'s scheme is in ``protocols``.

    Relative and anchor URLs, which carry no scheme, are always allowed.
    """
    scheme = _scheme(url)
    return scheme == "" or scheme in protocols
