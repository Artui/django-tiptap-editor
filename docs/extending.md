# Extending

Custom extensions and toolbar buttons are authored as plain `<script>` against the
already-loaded editor — **no bundler of your own**. The glue re-exports the TipTap
building blocks it contains on `DjangoTipTap.tiptap` (`Editor`, `Extension`, `Mark`,
`Node`, `mergeAttributes`).

## Custom extensions

```js
DjangoTipTap.registerExtension("callout", (config, ctx) => {
  const { Node, mergeAttributes } = ctx.tiptap;
  return Node.create({
    name: "callout",
    group: "block",
    content: "block+",
    parseHTML: () => [{ tag: "div.callout" }],
    renderHTML: ({ HTMLAttributes }) => ["div", mergeAttributes(HTMLAttributes, { class: "callout" }), 0],
  });
});
```

`factory(config, ctx)` returns an `Extension` (or array); `ctx = { tiptap, locale, t }`.
To activate it:

1. Register it (before mount — see [load order](#load-order)).
2. List its name in `config.extensions`.
3. Add the name to `TIPTAP_EXTRA_EXTENSIONS` so Python config validation accepts it.

```python
TIPTAP_EXTRA_EXTENSIONS = ["callout"]
TipTapWidget(config={"extensions": ["callout"]})
```

Built-in names are always active; unknown, unregistered names fail loudly at mount.

## Toolbar buttons

```js
DjangoTipTap.ui.registerButton("callout", {
  icon: "▣",
  title: "Callout",
  isActive: (editor) => editor.isActive("callout"),
  onClick: (editor) => editor.chain().focus().toggleWrap("callout").run(),
});
```

Then reference the key in `config.toolbar`. A button spec is either a command button
(`icon` + `onClick`, optional `isActive` / `isEnabled`) or a custom control
(`render(editor) -> { el, refresh? }`) that owns its DOM — that's how the built-in
font/colour/table menus are built.

## Load order

Registration must run before auto-mount. Load your registration script **after** the
editor assets; auto-mount runs on `DOMContentLoaded`, so a normal script placed after the
bundle (or `{% tiptap_media %}`) registers in time. For dynamically inserted editors, call
`DjangoTipTap.autoMount(root)` after registering, or use
[explicit init](api.md#explicit-init-path-b).

## Custom locales

```js
DjangoTipTap.registerLocale("de", { bold: "Fett", italic: "Kursiv" /* … */ });
```

Missing keys fall back to English. Select with `config.locale`.

## Semver

Custom-extension authoring is tied to the supported TipTap major; a TipTap major bump is
a major bump here too. See the [stability policy](semver.md).
