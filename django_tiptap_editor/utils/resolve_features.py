"""Resolve a config's ``features`` list to the full set of features it enables."""

from __future__ import annotations

from typing import Any

from django_tiptap_editor.constants import FEATURE_CORE, FEATURE_DEPENDENCIES


def resolve_features(config: dict[str, Any]) -> frozenset[str] | None:
    """Return every feature ``config`` turns on, or ``None`` when it restricts none.

    ``None`` is the unrestricted editor: no ``features`` key, which is every
    built-in extension and the markup of all of them. A list is a restriction, and
    the result is that list plus ``FEATURE_CORE`` plus whatever each entry cannot
    work without (``FEATURE_DEPENDENCIES``). The widget writes the result into
    ``data-tiptap-config`` so the browser mounts exactly this set; it restricts the
    editor only, and the server's sanitiser still allows the markup of every
    built-in extension.

    The list is assumed valid (``validate_config`` checks the names); an unknown
    name here would simply be carried through.
    """
    features = config.get("features")
    if features is None:
        return None
    resolved = set(FEATURE_CORE)
    pending = list(features)
    while pending:
        name = pending.pop()
        # Seen already, which also ends the walk: ``highlight`` leads to
        # ``backgroundColor`` leads to ``textStyle``, each reached once. Core
        # names declare no dependencies, so skipping them loses nothing.
        if name in resolved:
            continue
        resolved.add(name)
        pending.extend(FEATURE_DEPENDENCIES.get(name, ()))
    return frozenset(resolved)
