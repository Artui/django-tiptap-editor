"""Form widget that renders a TipTap-backed rich-text editor."""

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
    """Return ``config`` with ``features`` replaced by the full set it enables.

    The browser then mounts exactly the listed features, the core and their
    dependencies, sorted, and needs no closure of its own on this path. Done here,
    where the config is written, rather than in ``get_config``: that is the
    documented override point, and ``AdminTipTapWidget`` (or a project's subclass)
    replacing it would otherwise skip the resolution. ``None`` is the unrestricted
    editor, so the key is dropped rather than sent as ``null``: it is how one field
    lifts a project-wide ``features`` default. A new dict every time, so neither a
    widget's ``config=`` nor ``TIPTAP_DEFAULT_CONFIG`` is mutated.
    """
    if "features" not in config:
        return config
    resolved = resolve_features(config)
    rest = {key: value for key, value in config.items() if key != "features"}
    if resolved is None:
        return rest
    return {**rest, "features": sorted(resolved)}


class TipTapWidget(forms.Textarea):
    """A ``<textarea>`` carrying ``data-tiptap-config`` for the JS glue to mount.

    The textarea stays the form's serialization target; the glue writes
    ``editor.getHTML()`` back into ``textarea.value`` on every update, so a normal
    POST submits HTML — which the server sanitizes on the way in, because the
    glue runs in the browser and a client can post the field directly.

    The config is merged by ``get_config``, and a subclass that adds a layer
    decides where it goes: this class merges ``get_default_config()`` then the
    per-instance ``config=``, so the instance wins. ``AdminTipTapWidget`` inserts
    its own defaults *between* the two, so a per-instance ``config=`` still wins
    over them. Read the concrete ``get_config`` for the order that applies.
    Whatever ``get_config`` returns, a ``features`` list in it is written out
    resolved (core and dependencies included, sorted), so every subclass emits
    the same set the server's ``resolve_features`` computes.

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
        config = _with_resolved_features(self.get_config(widget_attrs))
        widget_attrs[CONFIG_ATTR] = json.dumps(config)
        widget_attrs[STORAGE_ATTR] = self.storage or get_storage_format()
        return context

    @property
    def media(self) -> forms.Media:
        # The committed self-contained bundle (default, node-free). External
        # asset mode is opt-in via the {% tiptap_media %} template tag.
        return forms.Media(js=[BUNDLE_JS], css={"all": [BUNDLE_CSS]})
