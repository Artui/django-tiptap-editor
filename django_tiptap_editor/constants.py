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
        "features",
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
# A table cell carries text-align from Tiptap 3 on, which parses a cell's inline
# text-align (or a legacy align attribute) and renders it back as a style.
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
CELL_STYLE_PROPERTIES = ("background-color", "text-align")

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
    "link": {"a": {"attrs": ("class", "href", "rel", "target", "title")}},
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

# The block tags in the vocabulary above that hold text a reader sees as its own
# block. On a field whose ``features`` leave one out, the sanitiser turns it into
# a paragraph boundary rather than unwrapping it, because unwrapping would run
# two headings, two list items or two cells into one line of text -- the same
# thing the editor does when such markup is pasted into it. The containers
# around them (lists, tables, rows, column groups) are simply unwrapped: what
# they hold decides where the paragraphs fall.
PARAGRAPH_BLOCK_TAGS = frozenset(
    {"h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "li", "td", "th"}
)

# Which feature each ProseMirror node type, mark type and feature-owned
# attribute of a stored JSON document belongs to: the vocabulary above, in the
# document's own names. A key is a node or mark type (``heading``), or
# ``type.attribute`` for an attribute another feature adds to a type
# (``textStyle.color`` is the ``color`` feature's, not textStyle's). Any other
# attribute goes with its type: a cell's ``align`` and ``backgroundColor`` are
# the table's, because the HTML side keeps them under the cell's own vocabulary.
# A restricted field narrows its document with this (``narrow_doc``); the JS
# suite holds it equal to the editor's schema through the vocabulary fixture.
DOCUMENT_FEATURES: dict[str, str] = {
    "doc": "document",
    "text": "text",
    "paragraph": "paragraph",
    "hardBreak": "hardBreak",
    "heading": "heading",
    "blockquote": "blockquote",
    "codeBlock": "codeBlock",
    "horizontalRule": "horizontalRule",
    "bulletList": "bulletList",
    "orderedList": "orderedList",
    "listItem": "listItem",
    "image": "image",
    "table": "table",
    "tableRow": "tableRow",
    "tableCell": "tableCell",
    "tableHeader": "tableHeader",
    "bold": "bold",
    "italic": "italic",
    "underline": "underline",
    "strike": "strike",
    "code": "code",
    "subscript": "subscript",
    "superscript": "superscript",
    "link": "link",
    "textStyle": "textStyle",
    "textStyle.color": "color",
    "textStyle.backgroundColor": "backgroundColor",
    "textStyle.fontFamily": "fontFamily",
    "textStyle.fontSize": "fontSize",
    "paragraph.textAlign": "textAlign",
    "heading.textAlign": "textAlign",
}

# Features that only add attributes or style properties to a type another
# feature owns, derived from the table above. Their HTML vocabulary names tags
# (textAlign's names h1-h6, because it aligns headings where headings exist), so
# a restricted schema takes their attributes and styles but never a tag from
# them: a field with alignment and no headings must not keep an <h2>.
DECORATING_FEATURES = frozenset(
    feature for key, feature in DOCUMENT_FEATURES.items() if "." in key
) - frozenset(feature for key, feature in DOCUMENT_FEATURES.items() if "." not in key)

# What a field with a ``features`` list always gets: the structure every document
# needs (document, text, paragraph), undo, the two cursors, and ``hardBreak``,
# which is core because Shift-Enter inside a list item and a pasted ``<br>`` both
# need it and dropping it would merge lines. Everything else in the vocabulary is
# a feature an author can leave out of one field.
FEATURE_CORE = frozenset(
    {"document", "text", "paragraph", "hardBreak", "history", "dropcursor", "gapcursor"}
)

# Features that cannot work without another. Listing a key pulls in its values, so
# a field naming ``table`` cannot mount a table without its rows and cells.
# Resolved by ``resolve_features`` on the server, where the result decides both
# what the widget mounts and what the field's HTML and JSON form fields keep, and
# restated, then held equal by a test, in the JS build for the entry point that
# bypasses Django. ``highlight`` is the same background-colour mark as
# ``backgroundColor`` under its toolbar name.
FEATURE_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "bulletList": ("listItem",),
    "orderedList": ("listItem",),
    "table": ("tableRow", "tableCell", "tableHeader"),
    # The parts lead back to the table because a row or cell is not a schema the
    # editor can mount without it, and a sanitiser keeping a cell with no table
    # around it would store markup no editor of the field can open: naming any
    # one of them must give the whole set.
    "tableRow": ("table",),
    "tableCell": ("table",),
    "tableHeader": ("table",),
    "fontFamily": ("textStyle",),
    "color": ("textStyle",),
    "backgroundColor": ("textStyle",),
    "highlight": ("backgroundColor", "textStyle"),
    "fontSize": ("textStyle",),
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

# Maximum nesting of any value in a stored JSON document, counting every object
# and array rather than only nodes. A node costs two levels (its object and the
# ``content`` array holding it), so a document at MAX_DOCUMENT_DEPTH reaches
# about 200 with its attrs and marks; this is twice that. The bound exists for
# ``json.dumps``, which Django's JSONField runs in ``validate`` and again on
# save, and which recurses per level: an array nested about 950 levels inside a
# node's ``attrs`` -- a 2 KB body that parses -- raised RecursionError there on
# Python 3.10.
MAX_JSON_DEPTH = 4 * MAX_DOCUMENT_DEPTH

# Empty base config: JS fills defaults for omitted keys, so Python keeps no
# duplicate default toolbar/extension lists that could drift from the glue.
DEFAULT_CONFIG: dict[str, object] = {}

# TipTap version the committed glue is built + validated against. Keep in sync
# with js/package.json (the build also bakes it into the glue for the
# external-mode startup version check).
TIPTAP_VERSION = "3.31.4"

# Bare `@tiptap/*` specifiers the glue ESM imports — the import map external mode
# must resolve. tests/utils/test_get_import_map.py reads the imports out of the
# committed tiptap.glue.esm.js and fails if this list differs from them.
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
    "@tiptap/extensions",
)

# CDN base for the default external-mode import map (verified to mount + edit
# without ProseMirror duplication when every specifier is pinned to one version).
ESM_CDN = "https://esm.sh"
