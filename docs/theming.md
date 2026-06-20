# Theming

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

### In CSS

```css
.django-tiptap {
  --tiptap-accent: #0b7285;
  --tiptap-radius: 12px;
  --tiptap-toolbar-bg: #f3f4f6;
}
```

### In JS

```js
DjangoTipTap.ui.setTokens({ accent: "#0b7285", radius: "12px" });
// bare keys are prefixed with --tiptap-; or pass full "--tiptap-…" names.
```

## Targeting parts

The shell uses stable, namespaced classes you can style directly: `.django-tiptap`
(shell), `.django-tiptap__toolbar`, `.django-tiptap__group`, `.django-tiptap__btn`
(`.is-active`), `.django-tiptap__content`, `.django-tiptap .ProseMirror` (the editing
surface), and the dropdown/menu/swatch/modal classes.

## Stability

Tokens and namespaced classes are the **stable** tier. Deeper region/shell renderer
overrides are on the roadmap and will ship flagged as evolving — see the
[stability policy](semver.md).
