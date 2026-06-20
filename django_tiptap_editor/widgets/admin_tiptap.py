"""Admin-sized variant of the TipTap widget."""

from __future__ import annotations

from typing import Any

from django_tiptap_editor.utils.get_default_config import get_default_config
from django_tiptap_editor.utils.validate_config import validate_config
from django_tiptap_editor.widgets.tiptap_widget import TipTapWidget


class AdminTipTapWidget(TipTapWidget):
    """``TipTapWidget`` tuned for the Django admin (taller by default).

    Config resolution: ``get_default_config()`` → ``admin_defaults`` →
    per-instance ``config=``.
    """

    admin_defaults: dict[str, Any] = {"height": "500px"}

    def get_config(self, attrs: dict[str, Any]) -> dict[str, Any]:
        merged = {**get_default_config(), **self.admin_defaults, **self.config}
        return validate_config(merged)
