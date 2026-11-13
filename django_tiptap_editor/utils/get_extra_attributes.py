from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from django.core.exceptions import ImproperlyConfigured

from django_tiptap_editor.constants import EXTRA_ATTRIBUTE_NAMES, EXTRA_ATTRIBUTE_TAGS
from django_tiptap_editor.utils.get_default_config import get_default_config


def _names(node_type: str, value: Any) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise ImproperlyConfigured(
            f"TipTap extraAttributes[{node_type!r}] must be a list of attribute names, "
            f"got {value!r}."
        )
    unknown = [name for name in value if name not in EXTRA_ATTRIBUTE_NAMES]
    if unknown:
        raise ImproperlyConfigured(
            f"TipTap extraAttributes[{node_type!r}] names unsupported attribute(s) "
            f"{unknown!r}. Allowed: {sorted(EXTRA_ATTRIBUTE_NAMES)}."
        )
    return tuple(dict.fromkeys(value))


def get_extra_attributes(config: Mapping[str, Any] | None = None) -> dict[str, tuple[str, ...]]:
    """Return the ``extraAttributes`` grant of ``config``, or of the project default config."""
    source = get_default_config() if config is None else config
    grant = source.get("extraAttributes")
    if grant is None:
        return {}
    if not isinstance(grant, Mapping):
        raise ImproperlyConfigured(
            f"TipTap extraAttributes must map a node type to a list of attribute names, "
            f"got {grant!r}."
        )
    unknown = [node_type for node_type in grant if node_type not in EXTRA_ATTRIBUTE_TAGS]
    if unknown:
        raise ImproperlyConfigured(
            f"TipTap extraAttributes names unsupported node type(s) {unknown!r}. "
            f"Allowed: {sorted(EXTRA_ATTRIBUTE_TAGS)}."
        )
    granted = {node_type: _names(node_type, names) for node_type, names in grant.items()}
    return {node_type: names for node_type, names in granted.items() if names}
