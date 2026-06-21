"""Form widget that renders a TipTap-backed rich-text editor."""

from __future__ import annotations

import json
from typing import Any

from django import forms

from django_tiptap_editor.constants import BUNDLE_CSS, BUNDLE_JS, CONFIG_ATTR, STORAGE_ATTR
from django_tiptap_editor.utils.get_default_config import get_default_config
from django_tiptap_editor.utils.get_storage_format import get_storage_format
from django_tiptap_editor.utils.validate_config import validate_config


class TipTapWidget(forms.Textarea):
    """A ``<textarea>`` carrying ``data-tiptap-config`` for the JS glue to mount.

    The textarea stays the form's serialization target; the glue writes
    ``editor.getHTML()`` back into ``textarea.value`` on every update, so a normal
    POST submits HTML. Resolution order for the config (last wins):
    ``get_default_config()`` → per-instance ``config=`` → subclass overrides.

    ``storage`` selects what the glue serializes: ``"html"`` (default) or
    ``"json"`` (a ``{doc, html}`` envelope, used by ``TipTapJSONField``). When
    ``None`` it resolves from ``settings.TIPTAP_STORAGE_FORMAT`` at render time.
    """

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
        widget_attrs[CONFIG_ATTR] = json.dumps(self.get_config(widget_attrs))
        widget_attrs[STORAGE_ATTR] = self.storage or get_storage_format()
        return context

    @property
    def media(self) -> forms.Media:
        # The committed self-contained bundle (default, node-free). External
        # asset mode is opt-in via the {% tiptap_media %} template tag.
        return forms.Media(js=[BUNDLE_JS], css={"all": [BUNDLE_CSS]})
