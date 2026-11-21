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
| `--tiptap-height` | Editing-area min-height (default `360px`) |
| `--tiptap-max-height` | Editing-area max-height; the content scrolls past it (default `none`) |
| `--tiptap-font` | Font family |
| `--tiptap-fg` / `--tiptap-bg` | Text / surface colour |
| `--tiptap-border` | Border colour: the editor's edge, the toolbar and group separators, the menu and panel borders, the footer, the source note, the modal header and the image picker (light `#858b97`, dark `#7a8190`) |
| `--tiptap-radius` | Corner radius |
| `--tiptap-toolbar-bg` | Toolbar background |
| `--tiptap-btn-fg` | Toolbar button colour |
| `--tiptap-btn-hover-bg` | Button hover background |
| `--tiptap-btn-active-bg` / `--tiptap-btn-active-fg` | Active button colours |
| `--tiptap-accent` | Links, focus, selected-image outline |
| `--tiptap-content-bg` / `--tiptap-content-fg` | Editing area and source view (light default: unset, so the area shows the shell's `--tiptap-bg` / `--tiptap-fg`) |
| `--tiptap-content-border` | Table cell borders in the editing area (light default: `#d0d5dd`, dark `#858d9b`) |
| `--tiptap-highlight-ink` | Text colour of a highlighted run that has no colour of its own (light default: unset, so it inherits) |
| `--tiptap-highlight-glyph-bg` / `--tiptap-highlight-glyph-fg` | The highlight button's glyph (light: `#fff3a3`, text inherits the button's) |
| `--tiptap-swatch-border` / `--tiptap-swatch-border-hover` | Colour swatch and custom-colour chip outline, and its hover |
| `--tiptap-shadow-color` | Shadow of the dropdown panels and the floating menus |
| `--tiptap-modal-shadow-color` / `--tiptap-overlay-bg` | Image-picker modal shadow and the overlay behind it |
| `--tiptap-color-scheme` | `color-scheme` of the shell and the picker modal, so the source textarea, the colour input and the focus ring follow the scheme (light default: unset, so they inherit the page's) |
| `--tiptap-modal-z` | `z-index` of the image-picker overlay, and of the open dropdown panels in a browser without the popover API (default `2000`) |

The defaults are declared on the document root with zero specificity
(`:where(:root, :host)`), and every editor inherits them. So a token set anywhere above an
editor reaches it, and any rule you write beats the default whichever stylesheet
loads last. From strongest to weakest:

1. a field's own `height` / `maxHeight` [config](configuration.md#heights), written
   on that editor's shell;
2. a token set on `.django-tiptap` or on an element around one editor;
3. a token set on `:root` / `html`, in CSS or with `ui.setTokens`, which writes there;
4. the built-in default.

The defaults are declared on `:host` as well (`:where(:root, :host)`), for a page
that loads the stylesheet inside a shadow root, as a web component wrapping the
editor does: `:root` matches nothing there. Inside a shadow root the defaults sit on
the host element, so a token set on the document's `:root` (including with
`ui.setTokens`) stops at the host; set it on the host element instead.

### In CSS

```css
:root {
  --tiptap-accent: #0b7285;
  --tiptap-radius: 12px;
}

/* Or for the editors in one part of the page only. */
.newsletter-form .django-tiptap {
  --tiptap-toolbar-bg: #f3f4f6;
}
```

### Stacking the picker over host modals

The image-picker overlay is portaled to `<body>`, so it sits outside the editor's
stacking context, at `z-index: 2000`, which clears common modal stacks (Bootstrap 3/4/5
use 1050–1060).

An open toolbar dropdown (font size, colour, table and the rest) stays inside the editor,
right after its trigger, and is shown as a popover in the browser's top layer, so the
shell's rounded, clipped edge cannot cut it off on a narrow or short field and no
`z-index` is involved. Because it stays a descendant of the editor, a modal's focus trap
(Bootstrap's, a native `<dialog>` opened with `showModal()`) treats it as inside the
modal. It is placed beside its trigger, flips above it or aligns to its end where the
viewport runs out, and follows it on scroll and resize. In a browser without the popover
API (before Chrome 114, Safari 17, Firefox 125) the panel is portaled instead: into the
nearest `dialog[open]`, `[role=dialog]`, `[aria-modal=true]` or `.modal` around the editor,
else to `<body>` or the shadow root that holds the editor, and there it takes the same
`z-index` as the picker. A native `<dialog>` scrolls its own overflow, so a portaled
panel near the dialog's edge can be clipped there. Escape on an open panel closes the
panel only, not the modal around it.

If your app embeds the editor inside a modal that stacks even higher, raise the knob —
no `!important` needed:

```css
:root {
  --tiptap-modal-z: 12000; /* above your host modal's z-index */
}
```

Set `--tiptap-modal-z` on `:root` (or `html`/`body`), **not** on `.django-tiptap`:
because the overlay is appended to `<body>`, it does not inherit custom properties
declared on the editor element. The same holds for the overlay's colours, border and
radius: a token set on `:root` themes the picker as well as the editors, one set on
`.django-tiptap` only the editors.

The dropdown panels are themed like the editor they belong to: a panel inherits the
editor's tokens, font, direction and language from the element it sits in, so a token
set on `.django-tiptap` or on a wrapper reaches the panel too. Where a panel is portaled
(no popover API), those values are copied onto it each time it opens instead, so a
`setTokens` call or a scheme switch while it is open shows the next time it opens; inside
a shadow root it is then a child of the shadow root, so an `overflow` or `contain` on the
shadow host itself still clips it.

### In JS

```js
DjangoTipTap.ui.setTokens({ accent: "#0b7285", radius: "12px" });
// bare keys are prefixed with --tiptap-; or pass full "--tiptap-…" names.
```

`setTokens` writes onto `document.documentElement`, so it is the page-wide layer (3
above): every editor follows it, including ones mounted later, and a field's own
`height` / `maxHeight` config still wins over a `height` / `max-height` token.

## Dark mode

The editor ships a dark colour set beside the light one. Light is the default, so a page
that does nothing renders as it did before.

### How it is picked

The scheme is read from one attribute on `<html>`, `data-tiptap-theme`:

| Value | Scheme |
| --- | --- |
| absent, or `"light"` | light |
| `"dark"` | dark |
| `"system"` | dark when the OS asks for it (`prefers-color-scheme: dark`), light otherwise |

The usual way to set it is the `TIPTAP_COLOR_SCHEME` setting:

```python
TIPTAP_COLOR_SCHEME = "system"  # or "dark", or "light" (the default)
```

Every widget then carries the value, and the glue writes it to `<html>` once, when the
first editor mounts. It is project-wide: a per-field scheme would have to sit on the
editor's shell, where it would beat the tokens you set on `:root`. The Django admin does
not follow its own theme toggle; set the setting there like anywhere else.

### Forcing it from the page

An attribute the page already set wins over the setting: the glue never overwrites it. So
a template can force a scheme, and a site with its own light/dark toggle drives the editor
by writing the attribute:

```html
<html data-tiptap-theme="dark">
```

```js
document.documentElement.dataset.tiptapTheme = userPrefersDark ? "dark" : "light";
```

There is no JavaScript API for it beyond that attribute. A page that mounts editors by
hand (`DjangoTipTap.init`, the `tiptap_config` tag) sets the attribute itself, since no
widget carries the setting there.

### Layering with your overrides

The scheme changes the built-in defaults and nothing else, so everything under
[Tokens](#tokens) still holds: a token you set on `:root`, with `ui.setTokens`, on
`.django-tiptap` or on a field beats either scheme. That has one consequence worth
planning for: **override colours in pairs.** A project that set `--tiptap-bg: #fff` for a
light look keeps that white background in the dark scheme, under the dark scheme's light
`--tiptap-fg`, and its text disappears. Set the foreground with the background
(`--tiptap-fg` with `--tiptap-bg`, `--tiptap-content-fg` with `--tiptap-content-bg`,
`--tiptap-btn-fg` with `--tiptap-toolbar-bg`), or scope an override to one scheme by
putting it under the attribute:

```css
html[data-tiptap-theme="dark"] {
  --tiptap-accent: #7cc4fa;
}

@media (prefers-color-scheme: dark) {
  html[data-tiptap-theme="system"] {
    --tiptap-accent: #7cc4fa;
  }
}
```

The dark values themselves live in private `--_tiptap-*` properties on `<html>`, which
the public tokens read. They are not part of the stable surface: set the `--tiptap-*`
tokens, never the private ones.

### Shadow roots

Custom properties inherit into a shadow root, but the scheme rules key on the page's
`<html data-tiptap-theme>`, and a rule in a stylesheet loaded inside a shadow root never
matches `<html>`. An editor in a shadow root therefore follows the page's scheme only when the
document itself loads the stylesheet: the widget's form Media already does, and a hand-built
page must link `tiptap.bundle.css` in the document too, besides any copy inside the shadow
root. Otherwise set the tokens on the host element, which beats the scheme there.

### Content colours

In the dark scheme the editing area is a dark paper a step lighter than the toolbar
(`--tiptap-content-bg`), and the chrome around it goes dark. Stored content is never
rewritten: the HTML a field posts is the same in both schemes. Two things follow:

- The built-in highlights are light backgrounds with no text colour, so the dark scheme
  gives a highlighted run that has no colour of its own a dark ink
  (`--tiptap-highlight-ink`). A run with an inline colour keeps it.
- An authored dark text colour (the `#1f2329` swatch, for one) stays dark, so it reads
  poorly on the dark paper. It is shown as stored, because that is how it will look where
  it is published. A project whose authors use dark text a lot can keep a light paper in
  the dark scheme by setting `--tiptap-content-bg` and `--tiptap-content-fg` (as a pair)
  to light values.

The editor's border marks where the editable field ends, so it meets WCAG 1.4.11 non-text
contrast (3:1) against the editor's own surfaces in both schemes: light `#858b97` (3.42 on
the shell, 3.22 on the toolbar), dark `#7a8190` (4.23 on the shell, 3.69 on the toolbar,
3.20 on the editing area). Against the page around it the ratio depends on the page. The
separators, menus, panels, footer, source note, modal header and image picker share the
token. Table cells do not: they read `--tiptap-content-border`, so a project that sets
`--tiptap-border` and wants tables to match sets `--tiptap-content-border` too. A project
that sets `--tiptap-border` keeps its value in both schemes, and the 3:1 is then its to
keep.

## Targeting parts

The shell uses stable, namespaced classes you can style directly: `.django-tiptap`
(shell), `.django-tiptap__toolbar`, `.django-tiptap__group`, `.django-tiptap__btn`
(`.is-active`), `.django-tiptap__content`, `.django-tiptap__statusbar`,
`.django-tiptap .ProseMirror` (the editing surface), and the dropdown/menu/swatch/modal
classes.

Toggle buttons (those with an active state, including `link` and any `ui.registerButton`
spec with `isActive`) carry `aria-pressed` alongside `.is-active`; dropdown triggers carry
`aria-expanded` alongside `.is-open`. Either attribute is a styling hook as good as the class.

### Dropdowns and the keyboard

The built-in dropdowns follow the WAI-ARIA Authoring Practices. Font size and font family
are menus of radio items (`role="menu"`, items `role="menuitemradio"` with `aria-checked` on
the current value, `Default` when none is set). Image, merge tags and table are menus of
actions (`role="menuitem"`, the table's groups divided by `role="separator"`). Text color
and highlight are non-modal dialogs (`role="dialog"`) because they hold the native colour
input: the swatches are buttons with `aria-pressed` on the current colour. Each trigger's
`aria-haspopup` names its popup, `"menu"` or `"dialog"`.

| Key | Where | What it does |
| --- | --- | --- |
| Enter, Space, ArrowDown | trigger | opens the panel and focuses the checked item (a size or family), the pressed swatch, else the first entry |
| ArrowUp | trigger | the same, but an action menu focuses its last item |
| ArrowDown, ArrowUp | menu | next or previous item, wrapping |
| Home, End | menu | first or last item |
| a letter or digit | menu | the next item whose label starts with it |
| Enter, Space | item | picks it; focus goes to the editor |
| Tab | panel | closes a menu and moves to the control after the trigger; walks a dialog's swatches, custom colour and Remove, and leaves it from the last |
| Shift+Tab | panel | back to the trigger: a menu closes, a dialog stays open |
| Escape | anywhere | closes the panel; focus goes back to the trigger if it was in the panel |

A menu keeps one item tabbable at a time (roving `tabindex`). Opening a panel with the
mouse leaves focus, and the editor's visible selection, where it was. A focused item
or swatch shows a `:focus-visible` ring in `--tiptap-accent` or `--tiptap-fg`, unlike the
fill (`.is-active`) or outline that marks the current value.

The font-size trigger shows the current size as text (`Default`, `16`) rather than a glyph:
`.django-tiptap__value-text` is the visible value and `.django-tiptap__value-sizer` an
invisible stack of every label in the same grid cell, which keeps the trigger as wide as
its widest label (in the active locale and `fontSizes`) so it does not shift as the caret
moves. Its accessible name is the `fontSizeValue` string (`"{name}: {value}"`, e.g.
`Font size: 16`); a locale registered with `registerLocale` can reword it.

A button given a [`toolbarLabels`](configuration.md) entry carries
`.django-tiptap__btn--labelled` and its text in `.django-tiptap__btn-label`, after the
glyph and before a dropdown's caret. The span does not wrap and ends in an ellipsis past
`16em`; the button grows to fit it. The toolbar wraps by group, and a group's own buttons
wrap too, so a narrow field never pushes one out of reach. On `fontSize`
the label takes the readout's place.

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
| `ctx.t` | the active translator (`ctx.t("bold")`; with named parameters, `ctx.t("fontSizeValue", { name: ctx.t("fontSize"), value: "16" })`, which fills `{name}` and `{value}`) |
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
order before `DOMContentLoaded`, so the registry is populated before mounting.

For non-`defer` setups, set `manualMount: true` on the field (or project-wide via
`TIPTAP_DEFAULT_CONFIG`). The automatic triggers — the initial scan and the `MutationObserver`
that auto-mounts swapped-in fields — then **skip** that field, so it never mounts before your
renderers exist. Register everything, then mount explicitly with `DjangoTipTap.autoMount()` (which
mounts every field, including `manualMount` ones) or `DjangoTipTap.init(el, config)`:

```html
<script src="…/tiptap.bundle.js"></script>
<script>
  DjangoTipTap.ui.setRenderer("toolbar", myToolbar);
  DjangoTipTap.registerExtension("myMark", myMarkFactory);
  DjangoTipTap.autoMount(); // now mount the manualMount fields
</script>
```
