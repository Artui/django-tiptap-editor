from __future__ import annotations

import json
from typing import Any

from django import forms

from django_tiptap_editor.constants import BUNDLE_CSS, BUNDLE_JS, CONFIG_ATTR, STORAGE_ATTR
from django_tiptap_editor.utils.get_default_config import get_default_config
from django_tiptap_editor.utils.get_storage_format import get_storage_format
from django_tiptap_editor.utils.resolve_features import resolve_features
from django_tiptap_editor.utils.validate_config import validate_config


def _with_resolved_features(config: dict[str, Any]) -> dict[str, Any]:
    """Return ``config`` with ``features`` replaced by the full set it enables."""
    if "features" not in config:
        return config
    resolved = resolve_features(config)
    rest = {key: value for key, value in config.items() if key != "features"}
    if resolved is None:
        return rest
    return {**rest, "features": sorted(resolved)}


class TipTapWidget(forms.Textarea):
    """A ``<textarea>`` carrying ``data-tiptap-config`` for the JS glue to mount."""

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        attrs: dict[str, Any] | None = None,
        storage: str | None = None,
    ) -> None:
        self.config: dict[str, Any] = config or {}
        self.storage = storage
        super().__init__(attrs)

    def get_config(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Return the validated, merged config written to the textarea."""
        merged = {**get_default_config(), **self.config}
        return validate_config(merged)

    def get_context(self, name: str, value: Any, attrs: dict[str, Any] | None) -> dict[str, Any]:
        context = super().get_context(name, value, attrs)
        widget_attrs = context["widget"]["attrs"]
        config = _with_resolved_features(self.get_config(widget_attrs))
        widget_attrs[CONFIG_ATTR] = json.dumps(config)
        widget_attrs[STORAGE_ATTR] = self.storage or get_storage_format()
        return context

    @property
    def media(self) -> forms.Media:
        # The committed self-contained bundle (default, node-free).
        return forms.Media(js=[BUNDLE_JS], css={"all": [BUNDLE_CSS]})
