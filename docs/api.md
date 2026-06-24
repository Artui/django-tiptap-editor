# API reference

## Python

### `TipTapWidget(forms.Textarea)`

`django_tiptap_editor.widgets.tiptap_widget.TipTapWidget`

```python
TipTapWidget(config=None, attrs=None, storage=None)
```

Renders a `<textarea>` carrying `data-tiptap-config`. Config resolution (last wins):
`get_default_config()` → the per-instance `config=` → subclass overrides
(`get_config(self, attrs)`). `class Media` emits the committed bundle. `storage` is
`"html"` (default) or `"json"`; when `None` it resolves from
`settings.TIPTAP_STORAGE_FORMAT`. See [Storage format](storage.md).

### `AdminTipTapWidget(TipTapWidget)`

`django_tiptap_editor.widgets.admin_tiptap.AdminTipTapWidget` — admin-sized variant
(taller default via `admin_defaults`).

### `TipTapModelAdminMixin`

`django_tiptap_editor.admin.mixin.TipTapModelAdminMixin` — mix in before
`admin.ModelAdmin`. Swaps `AdminTipTapWidget` onto `TextField`s.
`tiptap_fields = "__all__"` (default) or an explicit list of field names.

### `TipTapFormField(forms.CharField)`

`django_tiptap_editor.forms.fields.TipTapFormField` — a `CharField` whose default widget
is `TipTapWidget`.

### `TipTapJSONField(models.JSONField)`

`django_tiptap_editor.fields.tiptap_json_field.TipTapJSONField` — a model field storing a
`{doc, html}` envelope. The Python value is a `TipTapValue`; the `doc` is protocol-allowlisted
on save. Optional `link_protocols` / `image_protocols` tuples override the allowlists. Its form
field is `TipTapJSONFormField` (a `forms.Field` whose widget is `TipTapWidget(storage="json")`).
See [Storage format](storage.md).

### `TipTapValue`

`django_tiptap_editor.types.tiptap_value.TipTapValue` — frozen value with `.doc` (canonical
ProseMirror JSON) and `.html` (the editor-derived, safe HTML mirror). `str(value)` / `{{ value }}`
render the mirror. `TipTapValue.from_stored({...})` builds one from a `{doc, html}` mapping.

### `render_doc`

`django_tiptap_editor.utils.render_doc.render_doc(doc, *, link_protocols=…, image_protocols=…)`
— renders a ProseMirror `doc` dict to a safe HTML string in pure Python (no Node), covering the
package's node/mark set with protocol allowlisting + CSS validation. The
`{{ value|tiptap_html }}` filter wraps it (and uses a `TipTapValue`'s mirror when given one). See
[Storage format](storage.md#server-side-rendering-python).

### `BaseImageUploadView` / `ImageUploadError`

`django_tiptap_editor.views` — subclass `BaseImageUploadView` and implement
`save(self, file) -> str` to wire storage; see [Contracts](contracts.md).

### Template tags

```html
{% load tiptap %}
{% tiptap_media %}            {# editor assets for the active asset mode #}
{% tiptap_config %}           {# the default config as a JSON string #}
{{ value|tiptap_html }}       {# render a TipTapValue / doc to safe HTML #}
```

All of `TipTapWidget`, `AdminTipTapWidget`, `TipTapModelAdminMixin`, `TipTapFormField`,
`TipTapJSONField`, `TipTapJSONFormField`, `TipTapValue`, `BaseImageUploadView`,
`ImageUploadError`, `get_default_config`, `render_doc`, and `validate_config` are re-exported from
the package root.

## JavaScript — `window.DjangoTipTap`

```ts
DjangoTipTap.init(element, config)   // explicit mount; returns the editor
DjangoTipTap.get(id)                 // editor handle | null
DjangoTipTap.destroy(id)             // unmount + tear down the shell
DjangoTipTap.autoMount(root?)        // idempotent; mounts unbound textareas
DjangoTipTap.registerExtension(name, factory)
DjangoTipTap.registerLocale(code, strings)
DjangoTipTap.renderHTML(doc)         // ProseMirror JSON -> HTML string
DjangoTipTap.htmlToJSON(html)        // HTML -> ProseMirror JSON
DjangoTipTap.htmlToStored(html)      // HTML -> { doc, html } envelope (migration)
DjangoTipTap.ui.registerButton(key, spec)
DjangoTipTap.ui.setTokens(tokens)
DjangoTipTap.ui.setRenderer(region, fn)  // "toolbar" | "statusbar" | "bubbleMenu" | "floatingMenu"
DjangoTipTap.ui.setShellRenderer(fn)     // replace the whole shell (experimental)
DjangoTipTap.tiptap                  // re-exported primitives for authors
DjangoTipTap.supportedTipTapVersion  // the validated TipTap version
```

### Auto-mount (Path A)

Textareas rendered by the widget mount automatically. A `MutationObserver` watches the
DOM, so editors mount when inserted and tear down when removed — by htmx, Turbo, Unpoly,
Livewire, Alpine, Django admin inlines, or any script — with no framework-specific wiring.
The textarea is hidden and kept in sync; `destroy` is also exposed for manual teardown.

A **destructive swap re-mounts cleanly**: when a textarea is replaced by a fresh one with
the same `id` (an `outerHTML` swap), the stale editor is destroyed and the new node mounted
— never a duplicate or an orphaned shell. Place `{{ form.media }}` in the page `<head>`,
not inside a swapped partial (see
[Quickstart](quickstart.md#dynamic-forms-htmx-turbo-admin-inlines)).

### Explicit init (Path B)

For full control — and for the `onChange` callback, which can't travel through the JSON
`data-tiptap-config` attribute:

```html
<textarea id="ed"></textarea>
<script>
  const editor = DjangoTipTap.init(document.getElementById("ed"), {
    height: "400px",
    imageUploadUrl: "/editor/upload/",
    mergeTags: [{ label: "First name", value: "{{ first_name }}" }],
    onChange(html) { /* live preview, autosave, … */ },
  });
</script>
```

See [Extending](extending.md) for `registerExtension` / `registerButton` and the load
order rules, and [Theming](theming.md) for `setTokens`, `setRenderer`, and `setShellRenderer`.
