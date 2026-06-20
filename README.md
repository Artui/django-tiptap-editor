# django-tiptap-editor

[![CI](https://github.com/Artui/django-tiptap-editor/workflows/tests/badge.svg)](https://github.com/Artui/django-tiptap-editor/actions/workflows/tests.yml)
[![PyPI](https://img.shields.io/pypi/v/django-tiptap-editor.svg)](https://pypi.org/project/django-tiptap-editor/)
[![Python versions](https://img.shields.io/pypi/pyversions/django-tiptap-editor.svg)](https://pypi.org/project/django-tiptap-editor/)
[![Django versions](https://img.shields.io/pypi/djversions/django-tiptap-editor.svg)](https://pypi.org/project/django-tiptap-editor/)
[![License](https://img.shields.io/pypi/l/django-tiptap-editor.svg)](https://github.com/Artui/django-tiptap-editor/blob/main/LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A reusable, pip-installable Django package providing a **drop-in rich-text editor**
backed by [TipTap](https://tiptap.dev) (headless ProseMirror): a form `Widget`, an
admin widget, a `ModelAdmin` mixin, a settings default, and vendored static assets —
**node-free for consumers**.

## What this is

`django-tiptap-editor` fills the same integration role as `django-tinymce` — a form
widget with a config hook, an admin widget, a settings default, and committed static
assets — but it is **not** an API clone. It has its own clean, options-object surface
and its own config schema.

- Stored value is **HTML** (consumers render with `|safe`), never JSON.
- ProseMirror's schema *is* a sanitizer: scripts and unknown nodes are dropped on
  parse, and link/image protocols are allowlisted.
- Two committed asset modes: a self-contained **bundle** (default, fully node-free)
  and a **glue-only** ESM build for consumers who bring their own TipTap via CDN /
  import maps.
- Extensible without a node toolchain: a runtime registry for custom extensions,
  toolbar buttons, and layered theming.

## Status

🔨 **Early development.** The package is being built schema-first — the editor's
ProseMirror schema is designed to round-trip real-world authored HTML without loss
before the surrounding Django plumbing is finalized. The first published release will be
`0.1.0`; the source tree carries `0.0.0` until then. APIs are not yet stable.

## Installation

```bash
pip install django-tiptap-editor
```

(Not yet on PyPI — published at the `0.1.0` milestone.)

## Documentation

Full documentation is published at
[artui.github.io/django-tiptap-editor](https://artui.github.io/django-tiptap-editor/).

## License

MIT — see [LICENSE](LICENSE).
