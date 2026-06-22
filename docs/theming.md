# Theming

Theming is layered into tiers, **descending in stability**, so you lean on the lowest tier
that does the job and keep the smallest possible exposure to change:

| Tier | API | Stability |
| --- | --- | --- |
| 1 | `ui.setTokens` / CSS variables + `ui.registerButton` | **stable** |
| 2 | `ui.setRenderer(region, fn)` — `"toolbar"` \| `"statusbar"` \| `"bubbleMenu"` \| `"floatingMenu"` | **semi-stable** |
| 3 | `ui.setShellRenderer(fn)` | **advanced / experimental** |

The default, stable customization path is **design tokens** — a set of `--tiptap-*` CSS
custom properties. Set them in CSS or via JS; near-zero churn risk across minor releases.

## Tokens

| Token | Purpose |
| --- | --- |
| `--tiptap-height` | Editing-area min-height |
| `--tiptap-font` | Font family |
| `--tiptap-fg` / `--tiptap-bg` | Text / surface colour |
| `--tiptap-border` | Border colour |
| `--tiptap-radius` | Corner radius |
| `--tiptap-toolbar-bg` | Toolbar background |
| `--tiptap-btn-fg` | Toolbar button colour |
| `--tiptap-btn-hover-bg` | Button hover background |
| `--tiptap-btn-active-bg` / `--tiptap-btn-active-fg` | Active button colours |
| `--tiptap-accent` | Links, focus, selected-image outline |
| `--tiptap-modal-z` | Image-picker overlay `z-index` (default `2000`) |

### In CSS

```css
.django-tiptap {
  --tiptap-accent: #0b7285;
  --tiptap-radius: 12px;
  --tiptap-toolbar-bg: #f3f4f6;
}
```

### Stacking the picker over host modals

The image-picker overlay is portaled to `<body>`, so it sits outside the editor's
stacking context. It defaults to `z-index: 2000`, which clears common modal stacks
(Bootstrap 3/4/5 use 1050–1060). If your app embeds the editor inside a modal that
stacks even higher, raise the knob — no `!important` needed:

```css
:root {
  --tiptap-modal-z: 12000; /* above your host modal's z-index */
}
```

Set `--tiptap-modal-z` on `:root` (or `html`/`body`), **not** on `.django-tiptap`:
because the overlay is appended to `<body>`, it does not inherit custom properties
declared on the editor element. Every other token in the table above is read inside
`.django-tiptap` and can be set there as usual.

### In JS

```js
DjangoTipTap.ui.setTokens({ accent: "#0b7285", radius: "12px" });
// bare keys are prefixed with --tiptap-; or pass full "--tiptap-…" names.
```

## Targeting parts

The shell uses stable, namespaced classes you can style directly: `.django-tiptap`
(shell), `.django-tiptap__toolbar`, `.django-tiptap__group`, `.django-tiptap__btn`
(`.is-active`), `.django-tiptap__content`, `.django-tiptap__statusbar`,
`.django-tiptap .ProseMirror` (the editing surface), and the dropdown/menu/swatch/modal
classes.

## Region renderers (tier 2, semi-stable)

When tokens and classes aren't enough, replace a whole chrome **region** while keeping the
rest of the editor. `ui.setRenderer(region, fn)` registers a renderer for one region; `fn(ctx)`
returns a DOM node that *is* that region (a full replacement, not a wrapper).

Supported regions — **chrome** (laid out by the shell) and **floating** (selection-anchored
overlays):

- **`"toolbar"`** — replaces the default toolbar.
- **`"statusbar"`** — adds a bottom region (there is no default statusbar; nothing renders unless
  you register one). Add the `django-tiptap__statusbar` class for the built-in chrome look.
- **`"bubbleMenu"`** — shown over a **non-empty selection**.
- **`"floatingMenu"`** — shown at the cursor on an **empty text line**.

`ctx` exposes:

| Field | What it is |
| --- | --- |
| `ctx.editor` | the live TipTap `Editor` — read state, run commands, subscribe with `editor.on(...)` |
| `ctx.config` | the resolved per-editor config |
| `ctx.t` | the active translator (`ctx.t("bold")`) |
| `ctx.getButton(key)` | resolve a registered toolbar button spec, to reuse built-in controls |

```js
// A custom statusbar showing a live character count.
DjangoTipTap.ui.setRenderer("statusbar", (ctx) => {
  const el = document.createElement("div");
  el.className = "django-tiptap__statusbar";
  const update = () => { el.textContent = `${ctx.editor.getText().length} characters`; };
  ctx.editor.on("transaction", update);
  update();
  return el;
});
```

A region renderer returns a static node — wire your own reactivity off `ctx.editor` (as above).
The built-in toolbar's button-state refresh only applies to the *default* toolbar.

### Selection-anchored menus (bubble / floating)

`"bubbleMenu"` and `"floatingMenu"` are overlays positioned over the editor by the package (a
lean built-in positioner — no `tippy.js`). Your renderer supplies the contents; it's shown/hidden
and positioned automatically as the selection changes, and clamped within the editor box.

```js
// A bubble toolbar over selected text, reusing built-in button specs.
DjangoTipTap.ui.setRenderer("bubbleMenu", (ctx) => {
  const bar = document.createElement("div");
  for (const key of ["bold", "italic", "link"]) {
    const spec = ctx.getButton(key);
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "django-tiptap__btn";
    btn.innerHTML = spec.icon;
    btn.addEventListener("mousedown", (e) => e.preventDefault()); // keep the selection
    btn.addEventListener("click", () => spec.onClick(ctx.editor));
    bar.appendChild(btn);
  }
  return bar;
});
```

!!! warning "Keep the selection on click"
    A click that moves focus out of the editor dismisses the menu. Call `preventDefault` on
    `mousedown` in your controls (as above) — the same rule the built-in toolbar follows.

The built-in positioner is intentionally simple (it favours a tiny bundle over pixel-perfect
edge handling). For full control, render your own menu via [explicit init](api.md) and TipTap's
bubble/floating-menu extensions.

## Shell renderer (tier 3, experimental)

`ui.setShellRenderer(fn)` hands you the **entire** editor shell. `fn(ctx)` gets everything a
region renderer does **plus `ctx.content`** — the ProseMirror host element — and must return the
shell root with `ctx.content` placed somewhere inside it, or the editor won't be visible.

```js
DjangoTipTap.ui.setShellRenderer((ctx) => {
  const root = document.createElement("section");
  root.className = "my-editor-shell";
  // ... build your own toolbar/chrome here ...
  root.appendChild(ctx.content); // REQUIRED: the editing surface
  return root;
});
```

This is the most powerful and the **most likely to change** across minor releases — treat it as
experimental and pin your supported version range. See the [stability policy](semver.md).

## Load order

Renderers (like extensions and buttons) must be registered **before** auto-mount. Load your
registration script *after* the bundle/glue, both with `defer` — deferred scripts run in document
order before `DOMContentLoaded`, so the registry is populated before mounting. For non-`defer`
setups, set `manualMount: true` and call `DjangoTipTap.autoMount()` after registering.
