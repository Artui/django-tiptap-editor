"""Package-wide constants (the single multi-export module)."""

from __future__ import annotations

# data-* attribute carrying the per-field config JSON the JS glue reads.
CONFIG_ATTR = "data-tiptap-config"

# Asset delivery modes (see TIPTAP_ASSET_MODE).
ASSET_MODE_BUNDLE = "bundle"
ASSET_MODE_EXTERNAL = "external"
ASSET_MODES = frozenset({ASSET_MODE_BUNDLE, ASSET_MODE_EXTERNAL})

# Committed static artifacts, relative to the staticfiles namespace.
BUNDLE_JS = "django_tiptap_editor/tiptap.bundle.js"
BUNDLE_CSS = "django_tiptap_editor/tiptap.bundle.css"
GLUE_JS = "django_tiptap_editor/tiptap.glue.esm.js"
GLUE_CSS = "django_tiptap_editor/tiptap.glue.esm.css"

# Recognised top-level config keys. A typo'd key fails loudly (see
# validate_config); JS supplies defaults for any omitted key.
KNOWN_CONFIG_KEYS = frozenset(
    {
        "height",
        "locale",
        "manualMount",
        "toolbar",
        "extensions",
        "paragraphStyle",
        "imageListUrl",
        "imageUploadUrl",
        "imageFileTypes",
        "mergeTags",
        "linkProtocols",
    }
)

# Built-in extension names the JS glue resolves. Consumer-registered extensions
# are added to the allowlist via TIPTAP_EXTRA_EXTENSIONS. Kept in sync with the
# JS BUILTIN_NAMES set; extension names are otherwise opaque to Python.
BUILTIN_EXTENSIONS = frozenset(
    {
        "document",
        "text",
        "paragraph",
        "bold",
        "italic",
        "strike",
        "code",
        "codeBlock",
        "heading",
        "bulletList",
        "orderedList",
        "listItem",
        "blockquote",
        "horizontalRule",
        "hardBreak",
        "history",
        "dropcursor",
        "gapcursor",
        "underline",
        "textStyle",
        "fontFamily",
        "color",
        "backgroundColor",
        "highlight",
        "fontSize",
        "textAlign",
        "link",
        "image",
        "table",
        "tableRow",
        "tableCell",
        "tableHeader",
        "subscript",
        "superscript",
        "characterCount",
        "sourceView",
    }
)

# Empty base config: JS fills defaults for omitted keys, so Python keeps no
# duplicate default toolbar/extension lists that could drift from the glue.
DEFAULT_CONFIG: dict[str, object] = {}
