"""Template tags: ``{% tiptap_media %}`` and ``{% tiptap_config %}``.

(A template-tag module groups its tags by Django convention, like the
``constants`` module groups constants.)
"""

from __future__ import annotations

import json

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
from django_tiptap_editor.get_asset_mode import get_asset_mode
from django_tiptap_editor.get_default_config import get_default_config
from django_tiptap_editor.get_import_map import get_import_map

register = template.Library()


@register.simple_tag
def tiptap_media() -> SafeString:
    """Emit the editor's static assets for the active ``TIPTAP_ASSET_MODE``.

    Bundle mode: the self-contained IIFE bundle + CSS. External mode: an
    ``importmap`` (from ``TIPTAP_IMPORT_MAP``) followed by the glue ESM module +
    CSS, for consumers bringing their own TipTap via CDN.
    """
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
    """Return the project default config as a JSON string.

    Useful for hand-authored textareas:
    ``<textarea data-tiptap-config='{% tiptap_config %}'>``.
    """
    return mark_safe(json.dumps(get_default_config()))
