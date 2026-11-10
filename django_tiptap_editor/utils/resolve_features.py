from __future__ import annotations

from typing import Any

from django_tiptap_editor.constants import FEATURE_CORE, FEATURE_DEPENDENCIES


def resolve_features(config: dict[str, Any]) -> frozenset[str] | None:
    """Return every feature ``config`` turns on, or ``None`` when it restricts none."""
    features = config.get("features")
    if features is None:
        return None
    resolved = set(FEATURE_CORE)
    pending = list(features)
    while pending:
        name = pending.pop()
        if name in resolved:
            continue
        resolved.add(name)
        pending.extend(FEATURE_DEPENDENCIES.get(name, ()))
    return frozenset(resolved)
