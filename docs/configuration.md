# Configuration

The editor is configured per field (a `config` dict on the widget) and project-wide
(Django settings). Per-field config is merged over the project default, then written to
the textarea's `data-tiptap-config` attribute as JSON; the JS glue fills in defaults for
any omitted key.

## Config keys

| Key | Type | Notes |
| --- | --- | --- |
| `height` | str | Editor min-height, e.g. `"400px"`. |
| `locale` | str | `"en"` or `"sv"` built in; add more with `registerLocale`. |
| `manualMount` | bool | Opt the field out of auto-mount (initial scan + observer); mount it yourself after registering renderers. See [Theming → Load order](theming.md#load-order). |
| `enterKey` | str | Enter / Shift-Enter behaviour **outside lists**: `"paragraph"` (default — Enter splits into a new paragraph, Shift-Enter inserts a line break), `"hardBreak"` (Enter inserts a `<br>`), or `"swap"` (exchange the two). Inside a list item Enter always starts the next item and Shift-Enter always breaks the line — see [Extending → The Enter key](extending.md#the-enter-key-built-in). |
| `toolbar` | list[list[str]] | Groups of [button keys](#toolbar-buttons). Omit for the default. |
| `features` | list[str] | Built-in extensions this field's editor may use; everything else is off, shortcuts and paste included. Omit for every built-in. See [Restricting features](#restricting-features). |
| `extensions` | list[str] | Custom extension names (add them to `TIPTAP_EXTRA_EXTENSIONS`). Built-ins listed here change nothing; to turn built-ins off, use [`features`](#restricting-features). |
| `linkProtocols` | list[str] | Allowed link protocols. Default `["http","https","mailto","tel"]`. |
| `imageUploadUrl` | str | Enables image upload (see [Contracts](contracts.md)). |
| `imageListUrl` | str | Enables the library picker. |
| `imageFileTypes` | str | Comma-separated extensions for the upload dialog, e.g. `"png,jpg,gif"`. |
| `fontFamilies` | list[str] | Presets for the `fontFamily` dropdown; each a full CSS font stack (label = first segment, quotes stripped). Omit for the built-in list. |
| `fontSizes` | list[str] | Presets for the `fontSize` dropdown; each a CSS length like `"16px"` (label = value without `px`). Omit for the built-in list. |
| `textColors` | list[str] | Swatches for the `color` (text color) dropdown; each any CSS color. Omit for the built-in palette. |
| `highlightColors` | list[str] | Swatches for the `highlight` (background) dropdown; each any CSS color. Omit for the built-in palette. |
| `colorPicker` | bool | Adds a native color picker under both color swatch grids, for colors the palettes don't carry. Default `False`. |
| `imageResize` | bool | Drag handles on a selected image, setting the width/height the document asks for. Default `True`; set `False` to pin images to their inserted size. |
| `mergeTags` | list[{label, value}] | Items for the merge-tags menu; `value` is inserted verbatim. |

Unknown top-level keys, extension names that are neither built in nor in
`TIPTAP_EXTRA_EXTENSIONS`, and feature names that are not built in raise
`ImproperlyConfigured` — typos fail loudly.

```python
TipTapWidget(
    config={
        "height": "500px",
        "toolbar": [["bold", "italic", "link"], ["bulletList", "orderedList"]],
        "imageUploadUrl": "/editor/upload/",
        "fontFamilies": ["Arial, sans-serif", "Roboto, sans-serif"],
        "fontSizes": ["12px", "14px", "16px", "20px", "28px"],
        "textColors": ["#1f2329", "#e03e2d", "#3598db"],
        "highlightColors": ["#fff3a3", "#c8f7c5", "#bfe3ff"],
        "colorPicker": True,
        "imageResize": True,
        "mergeTags": [{"label": "First name", "value": "{{ first_name }}"}],
    }
)
```

### Toolbar buttons

`undo` `redo` · `bold` `italic` `underline` `strike` `code` · `fontSize` `fontFamily`
`color` `highlight` · `h1` `h2` `h3` `paragraph` · `bulletList` `orderedList`
`blockquote` · `alignLeft` `alignCenter` `alignRight` `alignJustify` · `image` `table` ·
`link` `unlink` `clearFormatting` · `sourceView` · `mergeTags` (opt-in).

A group is an inner array; groups render with separators. Register your own buttons with
[`ui.registerButton`](extending.md#toolbar-buttons).

### Restricting features

`toolbar` decides which buttons a field shows; `features` decides what its editor can do.
Leaving the heading buttons out of the toolbar does not stop an author typing `## `,
pressing Ctrl+Alt+2 or pasting an `<h2>`: each still reaches the heading extension. List
`features` and an extension that is not listed is not mounted, so none of those paths
produces its content.

```python
# An email body: inline formatting, links and lists, nothing else.
TipTapWidget(
    config={
        "features": ["bold", "italic", "underline", "link", "bulletList", "orderedList"],
        "toolbar": [["bold", "italic", "underline", "link"], ["bulletList", "orderedList"]],
    }
)
```

Omit `features` and every built-in is on, exactly as without the key. `[]` is valid and
leaves paragraphs, text and line breaks. A name that is not a built-in extension raises
`ImproperlyConfigured`; custom extensions are switched on through `extensions`, not here.
A project-wide `features` in `TIPTAP_DEFAULT_CONFIG` applies to every field, a field's own
list replaces it, and `"features": None` on one field gives that field every built-in again.

What a restricted field does in the browser:

- A built-in toolbar button whose feature is off is not rendered. An explicit `toolbar`
  that names one still works for the rest: the button is left out and the console warns
  once, naming the button and the missing feature. Groups left empty disappear, so no
  stray separator renders.
- A custom button declares what it needs with `requires` (see
  [Extending](extending.md#toolbar-buttons)); one without it is always shown.
- Image files dropped or pasted into a field without `image` are left alone: nothing is
  inserted and nothing is uploaded.
- JSON-stored content saved before a field was restricted still opens. If the field's
  schema cannot build the stored document, the editor loads the HTML mirror instead, which
  keeps the text and drops the unsupported markup, rather than opening empty.

The feature names, grouped:

<!-- features:groups -->
| Group | Features |
| --- | --- |
| Inline marks | `bold` `italic` `underline` `strike` `code` `subscript` `superscript` |
| Text style | `textStyle` `fontFamily` `fontSize` `color` `backgroundColor` `highlight` |
| Blocks | `heading` `blockquote` `codeBlock` `horizontalRule` `textAlign` |
| Lists | `bulletList` `orderedList` `listItem` |
| Links and media | `link` `image` |
| Tables | `table` `tableRow` `tableCell` `tableHeader` |
| Editor | `characterCount` `sourceView` |
<!-- /features:groups -->

**Always on**, whatever the list says: <!-- features:core -->`document` `dropcursor`
`gapcursor` `hardBreak` `history` `paragraph` `text`<!-- /features:core -->. Naming one of
them is accepted and changes nothing. `hardBreak` is core rather than a feature because
Shift-Enter inside a list item and a pasted `<br>` both need it: without it, lines an
author kept apart would merge.

**Dependencies are pulled in.** A feature that cannot work without another brings it
along, so naming `table` alone gives a table with rows and cells, and naming a row, cell
or header alone gives the whole table:

<!-- features:dependencies -->
| Listing | Also turns on |
| --- | --- |
| `backgroundColor` | `textStyle` |
| `bulletList` | `listItem` |
| `color` | `textStyle` |
| `fontFamily` | `textStyle` |
| `fontSize` | `textStyle` |
| `highlight` | `backgroundColor` `textStyle` |
| `orderedList` | `listItem` |
| `table` | `tableCell` `tableHeader` `tableRow` |
| `tableCell` | `table` |
| `tableHeader` | `table` |
| `tableRow` | `table` |
<!-- /features:dependencies -->

The widget writes the resolved set, listed features plus core plus dependencies, into
`data-tiptap-config`, and `django_tiptap_editor.utils.resolve_features` returns the same
set on the server.

`features` restricts the editor, not the server. Stored HTML is still sanitised against
the vocabulary of every built-in extension (see [Security](security.md)), so a client that
posts the field directly, skipping the editor, can still submit a heading to a field whose
editor cannot make one.

## Settings

| Setting | Default | Purpose |
| --- | --- | --- |
| `TIPTAP_DEFAULT_CONFIG` | `{}` | Config merged under every widget's per-field config. |
| `TIPTAP_ASSET_MODE` | `"bundle"` | `"bundle"` or `"external"` — see [Asset modes](asset-modes.md). |
| `TIPTAP_IMPORT_MAP` | CDN default | External mode: bare-specifier → URL map. |
| `TIPTAP_EXTRA_EXTENSIONS` | `[]` | Extra extensions accepted by config validation: a list of names, or a mapping of name to the HTML vocabulary each emits. A declared name is also an extra node/mark type `TipTapJSONField` accepts in a stored document. See [Extending](extending.md#declaring-what-an-extension-emits). |

```python
TIPTAP_DEFAULT_CONFIG = {"height": "450px", "locale": "sv"}
```

Settings are read lazily — importing the package never touches Django settings.
