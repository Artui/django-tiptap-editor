# API reference

## Python

### `TipTapWidget(forms.Textarea)`

`django_tiptap_editor.widgets.tiptap_widget.TipTapWidget`

```python
TipTapWidget(config=None, attrs=None)
```

Renders a `<textarea>` carrying `data-tiptap-config`. Config resolution (last wins):
`get_default_config()` → the per-instance `config=` → subclass overrides
(`get_config(self, attrs)`). `class Media` emits the committed bundle.

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
`BaseImageUploadView`, `ImageUploadError`, `get_default_config`, and `validate_config`
are re-exported from the package root.

## JavaScript — `window.DjangoTipTap`

```ts
DjangoTipTap.init(element, config)   // explicit mount; returns the editor
DjangoTipTap.get(id)                 // editor handle | null
DjangoTipTap.destroy(id)             // unmount + tear down the shell
DjangoTipTap.autoMount(root?)        // idempotent; mounts unbound textareas
DjangoTipTap.registerExtension(name, factory)
DjangoTipTap.registerLocale(code, strings)
DjangoTipTap.ui.registerButton(key, spec)
DjangoTipTap.ui.setTokens(tokens)
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
order rules, and [Theming](theming.md) for `setTokens`.
