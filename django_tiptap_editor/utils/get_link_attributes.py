"""Resolve a link's safe ``target`` / ``rel`` pair (internal helper)."""

from __future__ import annotations

from django_tiptap_editor.constants import LINK_BLANK_REL, LINK_REL_TOKENS, LINK_TARGETS


def get_link_attributes(target: object, rel: object) -> tuple[str, str]:
    """Return the ``(target, rel)`` a stored link may carry, ``""`` for omitted.

    A document written by something other than the editor (an API, an import, a
    hand-edit) can name any ``target`` and any ``rel``. ``rel="opener"`` in
    particular re-enables the ``window.opener`` handle that ``target="_blank"``
    implies away, handing the opened page a live reference back to the one the
    reader came from. So the target is restricted to a frame keyword this package
    emits, the rel is reduced to known-safe tokens, and a link that does open a
    new context always carries ``noopener noreferrer``.
    """
    safe_target = str(target) if target in LINK_TARGETS else ""
    tokens = (
        [token for token in str(rel).lower().split() if token in LINK_REL_TOKENS]
        if isinstance(rel, str)
        else []
    )
    if safe_target == "_blank":
        tokens = list(LINK_BLANK_REL) + [t for t in tokens if t not in LINK_BLANK_REL]
    return safe_target, " ".join(tokens)
