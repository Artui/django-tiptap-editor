"""Package-wide constants (the single multi-export module)."""

from __future__ import annotations

# data-* attribute carrying the per-field config JSON the JS glue reads.
CONFIG_ATTR = "data-tiptap-config"

# data-* attribute telling the glue which storage format to serialize into the
# textarea.
STORAGE_ATTR = "data-tiptap-storage"

# Storage formats (see TIPTAP_STORAGE_FORMAT). "html" is the default, zero-config
# path (editor.getHTML()); "json" stores a {doc, html} envelope — the canonical
# ProseMirror document plus a derived HTML mirror (TipTapJSONField).
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
        "enterKey",
        "toolbar",
        "extensions",
        "paragraphStyle",
        "imageListUrl",
        "imageUploadUrl",
        "imageFileTypes",
        "mergeTags",
        "linkProtocols",
        "fontFamilies",
        "fontSizes",
        "textColors",
        "highlightColors",
        "colorPicker",
        "imageResize",
    }
)

# Allowed values for the ``enterKey`` config key (Enter / Shift-Enter behaviour):
# "paragraph" (default) keeps a paragraph split, "hardBreak" makes Enter a <br>,
# "swap" exchanges the two. Kept in sync with the JS EnterKeyMode union.
ENTER_KEY_MODES = frozenset({"paragraph", "hardBreak", "swap"})

# Inline-style properties each style-bearing extension may put on a tag. These
# are the vocabulary the editor itself emits: BlockStyle writes margin /
# margin-block-end / padding-left on paragraphs and headings, TextAlign adds
# text-align, the TextStyle family writes colour / font declarations on a span,
# the inline image keeps its layout style, and the table view sizes columns.
BLOCK_STYLE_PROPERTIES = ("margin", "margin-block-end", "padding-left")
TEXT_ALIGN_PROPERTIES = ("text-align",)
TEXT_STYLE_PROPERTIES = ("background-color", "color", "font-family", "font-size")
IMAGE_STYLE_PROPERTIES = (
    "border",
    "border-radius",
    "display",
    "float",
    "height",
    "margin",
    "margin-bottom",
    "margin-left",
    "margin-right",
    "margin-top",
    "padding",
    "padding-bottom",
    "padding-left",
    "padding-right",
    "padding-top",
    "vertical-align",
    "width",
)
TABLE_STYLE_PROPERTIES = ("min-width", "width")
CELL_STYLE_PROPERTIES = ("background-color",)

# Values a link's ``target`` may take, and the ``rel`` tokens that survive. A
# stored ``rel="opener"`` re-enables the ``window.opener`` handle that
# ``target="_blank"`` otherwise implies away, so rel is an allowlist of tokens
# rather than a passthrough, and _blank always carries noopener noreferrer.
LINK_TARGETS = frozenset({"_blank", "_self"})
LINK_REL_TOKENS = frozenset({"nofollow", "noopener", "noreferrer", "sponsored", "ugc"})
LINK_BLANK_REL = ("noopener", "noreferrer")

# The HTML vocabulary of every built-in extension: which tags it can emit, and
# the attributes and inline-style properties it puts on them. This is the single
# vocabulary shared by the editor and the server -- BUILTIN_EXTENSIONS is derived
# from its keys, and get_html_schema unions the entries into the allowlist
# sanitize_html enforces, so what the editor can produce and what the server
# accepts cannot drift apart. Kept in sync with the JS BUILTIN_NAMES set; an
# extension with no markup of its own (history, cursors, character count, source
# view) declares an empty vocabulary rather than being absent.
EXTENSION_HTML_VOCABULARY: dict[str, dict[str, dict[str, tuple[str, ...]]]] = {
    "document": {},
    "text": {},
    "paragraph": {"p": {"styles": BLOCK_STYLE_PROPERTIES}},
    "bold": {"strong": {}},
    "italic": {"em": {}},
    "strike": {"s": {}},
    "code": {"code": {}},
    "codeBlock": {"pre": {}, "code": {"attrs": ("class",)}},
    "heading": {f"h{level}": {"styles": BLOCK_STYLE_PROPERTIES} for level in range(1, 7)},
    "bulletList": {"ul": {}},
    "orderedList": {"ol": {"attrs": ("start", "type")}},
    "listItem": {"li": {}},
    "blockquote": {"blockquote": {}},
    "horizontalRule": {"hr": {}},
    "hardBreak": {"br": {}},
    "history": {},
    "dropcursor": {},
    "gapcursor": {},
    "underline": {"u": {}},
    "textStyle": {"span": {}},
    "fontFamily": {"span": {"styles": ("font-family",)}},
    "color": {"span": {"styles": ("color",)}},
    "backgroundColor": {"span": {"styles": ("background-color",)}},
    "highlight": {"span": {"styles": ("background-color",)}},
    "fontSize": {"span": {"styles": ("font-size",)}},
    "textAlign": {
        tag: {"styles": TEXT_ALIGN_PROPERTIES} for tag in ("p", "h1", "h2", "h3", "h4", "h5", "h6")
    },
    "link": {"a": {"attrs": ("class", "href", "rel", "target")}},
    "image": {
        "img": {
            "attrs": ("alt", "height", "src", "title", "width"),
            "styles": IMAGE_STYLE_PROPERTIES,
        }
    },
    "table": {
        "table": {"styles": TABLE_STYLE_PROPERTIES},
        "colgroup": {},
        "col": {"styles": TABLE_STYLE_PROPERTIES},
        "tbody": {},
    },
    "tableRow": {"tr": {}},
    "tableCell": {
        "td": {"attrs": ("colspan", "colwidth", "rowspan"), "styles": CELL_STYLE_PROPERTIES}
    },
    "tableHeader": {
        "th": {"attrs": ("colspan", "colwidth", "rowspan"), "styles": CELL_STYLE_PROPERTIES}
    },
    "subscript": {"sub": {}},
    "superscript": {"sup": {}},
    "characterCount": {},
    "sourceView": {},
}

# Keys a single extension vocabulary entry may carry (also validated for the
# per-tag vocabularies a project declares in TIPTAP_EXTRA_EXTENSIONS).
VOCABULARY_KEYS = frozenset({"attrs", "styles"})

# Built-in extension names the JS glue resolves, derived from the vocabulary
# above so the two can never list different names. Consumer-registered
# extensions are added to the allowlist via TIPTAP_EXTRA_EXTENSIONS.
BUILTIN_EXTENSIONS = frozenset(EXTENSION_HTML_VOCABULARY)

# Tags a project may never add through TIPTAP_EXTRA_EXTENSIONS: each one either
# executes script, loads a document, or rewrites how the rest of the page
# resolves URLs, so allowing one would defeat the sanitiser outright.
FORBIDDEN_TAGS = frozenset(
    {
        "base",
        "embed",
        "form",
        "frame",
        "frameset",
        "iframe",
        "link",
        "meta",
        "noscript",
        "object",
        "script",
        "style",
        "svg",
        "template",
    }
)

# Maximum node nesting a stored document may carry. The pure-Python walkers
# (sanitize_doc, render_doc) recurse per level, so an unbounded document is a
# cheap way to blow the interpreter's stack; a document deeper than this is
# rejected as invalid instead of raising RecursionError somewhere downstream.
# Real content sits one to two orders of magnitude below the limit.
MAX_DOCUMENT_DEPTH = 100

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
