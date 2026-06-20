# django-tiptap-editor

A reusable, pip-installable Django package providing a drop-in rich-text editor backed
by [TipTap](https://tiptap.dev) (headless ProseMirror): a form `Widget`, an admin
widget, a `ModelAdmin` mixin, a settings default, and vendored static assets — node-free
for consumers.

!!! warning "Early development"
    This package is being built schema-first. APIs are not yet stable and the first
    published release will be `0.1.0`. See the
    [GitHub repository](https://github.com/Artui/django-tiptap-editor) for the design
    plan and progress.

## Installation

```bash
pip install django-tiptap-editor
```

## Why this exists

- Stored value is **HTML** (render with `|safe`), never JSON.
- ProseMirror's schema *is* a sanitizer — scripts and unknown nodes are dropped on
  parse; link/image protocols are allowlisted.
- Two committed asset modes: a self-contained **bundle** (default) and a **glue-only**
  ESM build for bring-your-own-TipTap via CDN / import maps.
- Custom extensions, toolbar buttons, and layered theming — all without a node
  toolchain in the consuming app.
