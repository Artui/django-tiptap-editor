from __future__ import annotations

import json
from typing import Any

from django import template
from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.safestring import SafeString, mark_safe

from django_tiptap_editor.constants import (
    ASSET_MODE_EXTERNAL,
    BUNDLE_CSS,
    BUNDLE_JS,
    GLUE_CSS,
    GLUE_JS,
)
from django_tiptap_editor.types.tiptap_value import TipTapValue
from django_tiptap_editor.utils.get_asset_mode import get_asset_mode
from django_tiptap_editor.utils.get_default_config import get_default_config
from django_tiptap_editor.utils.get_extra_attributes import get_extra_attributes
from django_tiptap_editor.utils.get_import_map import get_import_map
from django_tiptap_editor.utils.render_doc import render_doc
from django_tiptap_editor.utils.sanitize_html import sanitize_html

register = template.Library()


@register.simple_tag
def tiptap_media() -> SafeString:
    """Emit the editor's static assets for the active ``TIPTAP_ASSET_MODE``."""
    if get_asset_mode() == ASSET_MODE_EXTERNAL:
        import_map = mark_safe(json.dumps({"imports": get_import_map()}))
        return format_html(
            '<script type="importmap">{}</script>\n'
            '<link rel="stylesheet" href="{}">\n'
            '<script type="module" src="{}"></script>',
            import_map,
            static(GLUE_CSS),
            static(GLUE_JS),
        )
    return format_html(
        '<link rel="stylesheet" href="{}">\n<script src="{}" defer></script>',
        static(BUNDLE_CSS),
        static(BUNDLE_JS),
    )


@register.simple_tag
def tiptap_config() -> SafeString:
    """Return the project default config as a JSON string."""
    return mark_safe(json.dumps(get_default_config()))


@register.filter
def tiptap_html(value: Any) -> SafeString:
    """Render any stored TipTap value to safe HTML — the way to display content."""
    if isinstance(value, TipTapValue):
        return mark_safe(str(value.html))
    if isinstance(value, str):
        return sanitize_html(value)
    return render_doc(value, extra_attributes=get_extra_attributes())
