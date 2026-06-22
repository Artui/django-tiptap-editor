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
| `enterKey` | str | Enter / Shift-Enter behaviour: `"paragraph"` (default — Enter splits into a new paragraph, Shift-Enter inserts a line break), `"hardBreak"` (Enter inserts a `<br>`), or `"swap"` (exchange the two). |
| `toolbar` | list[list[str]] | Groups of [button keys](#toolbar-buttons). Omit for the default. |
| `extensions` | list[str] | Extension names. Built-ins are always on; list custom ones (and add them to `TIPTAP_EXTRA_EXTENSIONS`). |
| `linkProtocols` | list[str] | Allowed link protocols. Default `["http","https","mailto","tel"]`. |
| `imageUploadUrl` | str | Enables image upload (see [Contracts](contracts.md)). |
| `imageListUrl` | str | Enables the library picker. |
| `imageFileTypes` | str | Comma-separated extensions for the upload dialog, e.g. `"png,jpg,gif"`. |
| `mergeTags` | list[{label, value}] | Items for the merge-tags menu; `value` is inserted verbatim. |

Unknown top-level keys, and extension names that are neither built in nor in
`TIPTAP_EXTRA_EXTENSIONS`, raise `ImproperlyConfigured` — typos fail loudly.

```python
TipTapWidget(config={
    "height": "500px",
    "toolbar": [["bold", "italic", "link"], ["bulletList", "orderedList"]],
    "imageUploadUrl": "/editor/upload/",
    "mergeTags": [{"label": "First name", "value": "{{ first_name }}"}],
})
```

### Toolbar buttons

`undo` `redo` · `bold` `italic` `underline` `strike` `code` · `fontSize` `fontFamily`
`color` `highlight` · `h1` `h2` `h3` `paragraph` · `bulletList` `orderedList`
`blockquote` · `alignLeft` `alignCenter` `alignRight` `alignJustify` · `image` `table` ·
`link` `unlink` `clearFormatting` · `sourceView` · `mergeTags` (opt-in).

A group is an inner array; groups render with separators. Register your own buttons with
[`ui.registerButton`](extending.md#toolbar-buttons).

## Settings

| Setting | Default | Purpose |
| --- | --- | --- |
| `TIPTAP_DEFAULT_CONFIG` | `{}` | Config merged under every widget's per-field config. |
| `TIPTAP_ASSET_MODE` | `"bundle"` | `"bundle"` or `"external"` — see [Asset modes](asset-modes.md). |
| `TIPTAP_IMPORT_MAP` | CDN default | External mode: bare-specifier → URL map. |
| `TIPTAP_EXTRA_EXTENSIONS` | `[]` | Extra extension names accepted by config validation. |

```python
TIPTAP_DEFAULT_CONFIG = {"height": "450px", "locale": "sv"}
```

Settings are read lazily — importing the package never touches Django settings.
