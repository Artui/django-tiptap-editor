from __future__ import annotations

from django_tiptap_editor.constants import LINK_BLANK_REL, LINK_REL_TOKENS, LINK_TARGETS


def get_link_attributes(target: object, rel: object) -> tuple[str, str]:
    """Return the ``(target, rel)`` a stored link may carry, ``""`` for omitted."""
    safe_target = target if isinstance(target, str) and target in LINK_TARGETS else ""
    tokens = (
        [token for token in str(rel).lower().split() if token in LINK_REL_TOKENS]
        if isinstance(rel, str)
        else []
    )
    if safe_target == "_blank":
        tokens = list(LINK_BLANK_REL) + [t for t in tokens if t not in LINK_BLANK_REL]
    return safe_target, " ".join(tokens)
