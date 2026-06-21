"""Package-wide constants (the single multi-export module)."""

from __future__ import annotations

# data-* attribute carrying the per-field config JSON the JS glue reads.
CONFIG_ATTR = "data-tiptap-config"

# data-* attribute telling the glue what to serialize into the textarea:
# "html" (editor.getHTML()) or "json" (a {doc, html} envelope). See
# TIPTAP_STORAGE_FORMAT / TipTapJSONField.
STORAGE_ATTR = "data-tiptap-storage"

# Storage formats (see TIPTAP_STORAGE_FORMAT). "html" is the default, zero-config
# path; "json" stores the canonical ProseMirror document plus a derived HTML
# mirror (TipTapJSONField).
STORAGE_FORMAT_HTML = "html"
STORAGE_FORMAT_JSON = "json"
STORAGE_FORMATS = frozenset({STORAGE_FORMAT_HTML, STORAGE_FORMAT_JSON})

# Protocol allowlists enforced when validating a stored ProseMirror document
# (sanitize_doc). Mirror the JS link/image protocol handling; a scheme outside
# these is stripped. Relative/anchor URLs (no scheme) are always allowed.
DEFAULT_LINK_PROTOCOLS = ("http", "https", "mailto", "tel")
DEFAULT_IMAGE_PROTOCOLS = ("http", "https", "data")

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

# TipTap version the committed glue is built + validated against. Keep in sync
# with js/package.json (the build also bakes it into the glue for the
# external-mode startup version check).
TIPTAP_VERSION = "2.27.2"

# Bare `@tiptap/*` specifiers the glue ESM imports — the import map external mode
# must resolve. (Matches the externalised imports in tiptap.glue.esm.js.)
GLUE_IMPORT_SPECIFIERS = (
    "@tiptap/core",
    "@tiptap/starter-kit",
    "@tiptap/extension-underline",
    "@tiptap/extension-text-style",
    "@tiptap/extension-font-family",
    "@tiptap/extension-color",
    "@tiptap/extension-text-align",
    "@tiptap/extension-link",
    "@tiptap/extension-image",
    "@tiptap/extension-table",
    "@tiptap/extension-table-row",
    "@tiptap/extension-table-cell",
    "@tiptap/extension-table-header",
    "@tiptap/extension-subscript",
    "@tiptap/extension-superscript",
    "@tiptap/extension-character-count",
)

# CDN base for the default external-mode import map (verified to mount + edit
# without ProseMirror duplication when every specifier is pinned to one version).
ESM_CDN = "https://esm.sh"
