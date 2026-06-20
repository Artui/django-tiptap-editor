# django-tiptap-editor

A reusable rich-text editor for Django, backed by [TipTap](https://tiptap.dev)
(headless ProseMirror): a form `Widget`, an admin widget, a `ModelAdmin` mixin, a
settings-driven config, and committed static assets — **node-free for consumers**.

## Highlights

- **Stores HTML** (render with `|safe`), never JSON.
- **Safe by construction** — ProseMirror's schema drops scripts and unknown nodes on
  parse; link and image protocols are allowlisted. See [Security](security.md).
- **Node-free** — ships a committed, self-contained bundle. An optional glue-only ESM
  build supports bring-your-own-TipTap via CDN / import maps. See [Asset modes](asset-modes.md).
- **Full editor** — formatting, font size/family, colour, highlight, headings, lists,
  alignment, links, images, tables, and a raw-HTML source view.
- **Image upload + library picker**, **merge tags**, and **en/sv i18n** built in.
- **Extensible without a build step** — register custom extensions and toolbar buttons,
  and re-theme via CSS variables. See [Extending](extending.md) and [Theming](theming.md).

## Get started

- [Installation](installation.md)
- [Quickstart](quickstart.md) — a form field and the admin mixin
- [Configuration](configuration.md) — the config schema and Django settings
- [API reference](api.md) — widgets, admin mixin, form field, views, and the JS API

## Coming from another editor?

Swapping editors is a content-validation exercise, not an automatic conversion — see
[Migrating](recipes/migrating-from-tinymce.md), which centers on running the fidelity
corpus over your real content first.
