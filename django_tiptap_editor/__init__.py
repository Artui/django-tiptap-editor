"""Drop-in TipTap (ProseMirror) rich-text editor widget for Django forms and admin."""

from __future__ import annotations

from django_tiptap_editor.admin.mixin import TipTapModelAdminMixin
from django_tiptap_editor.forms.fields import TipTapFormField
from django_tiptap_editor.utils.get_default_config import get_default_config
from django_tiptap_editor.utils.validate_config import validate_config
from django_tiptap_editor.version import __version__
from django_tiptap_editor.widgets.admin_tiptap import AdminTipTapWidget
from django_tiptap_editor.widgets.tiptap_widget import TipTapWidget

__all__ = [
    "AdminTipTapWidget",
    "TipTapFormField",
    "TipTapModelAdminMixin",
    "TipTapWidget",
    "__version__",
    "get_default_config",
    "validate_config",
]
