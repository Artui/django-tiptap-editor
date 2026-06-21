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

### `BaseImageUploadView` / `ImageUploadError`

`django_tiptap_editor.views` — subclass `BaseImageUploadView` and implement
`save(self, file) -> str` to wire storage; see [Contracts](contracts.md).

### Template tags

```html
{% load tiptap %}
{% tiptap_media %}   {# editor assets for the active asset mode #}
{% tiptap_config %}  {# the default config as a JSON string #}
```

All of `TipTapWidget`, `AdminTipTapWidget`, `TipTapModelAdminMixin`, `TipTapFormField`,
`TipTapJSONField`, `TipTapJSONFormField`, `TipTapValue`, `BaseImageUploadView`,
`ImageUploadError`, `get_default_config`, and `validate_config` are re-exported from the package
root.

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
DjangoTipTap.ui.setRenderer(region, fn)  // replace a region: "toolbar" | "statusbar"
DjangoTipTap.ui.setShellRenderer(fn)     // replace the whole shell (experimental)
DjangoTipTap.tiptap                  // re-exported primitives for authors
DjangoTipTap.supportedTipTapVersion  // the validated TipTap version
```

### Auto-mount (Path A)

By default, textareas rendered by the widget mount automatically (on load and on
`formset:added` / `django:added` / `htmx:afterSwap`). The textarea is hidden and kept in
sync; removing it is handled by `destroy`.

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
