# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.1] — 2026-06-24

### Changed

- **Framework-agnostic auto-mount.** Editors now mount and tear down via a single
  `MutationObserver` instead of a fixed set of framework events. A widget inserted
  into the DOM by htmx, Turbo, Unpoly, Livewire, Alpine, Django admin inlines, or
  any script mounts automatically, and removing it disposes its editor — with no
  per-framework wiring. ProseMirror's own DOM churn is ignored, so the observer
  stays cheap on a live page. `{% tiptap_media %}` / `{{ form.media }}` placement
  is unchanged.

### Fixed

- **Editor re-mounts cleanly after a destructive swap.** When a form was
  re-rendered via an `outerHTML` swap (e.g. returning validation errors), the
  server emits a fresh `<textarea>` with the same Django `id`, but the glue keyed
  liveness to its instances map and never tore the old editor down — so a bare,
  unstyled textarea appeared on top of an orphaned editor that only synced one
  way ([#25](https://github.com/Artui/django-tiptap-editor/issues/25)). Mounting
  is now keyed to the live DOM: a stale same-`id` instance whose node has left the
  document is destroyed and the new textarea is mounted in its place. A re-executed
  bundle (e.g. `{{ form.media }}` re-injected inside the swapped fragment) is now a
  no-op instead of clobbering the live glue module.
- **Image picker overlay no longer lingers after teardown.** The library image
  picker portals its overlay to `<body>` and registers a `document` key handler;
  if the editor was removed (e.g. a destructive DOM swap) while the picker was
  open, both were left orphaned over the page. They are now disposed when the
  editor is destroyed.
- **`DjangoTipTap.version` reports the real package version.** It was a hardcoded
  `0.0.0` placeholder; it is now injected from `version.py` at build time (`make
  release-bump` rebuilds the bundle, and CI's bundle diff-check keeps it in sync).

## [0.3.0] — 2026-06-22

### Added

- **Configurable Enter key.** A new `enterKey` config option controls Enter / Shift-Enter
  behaviour without writing JS: `"paragraph"` (default — Enter splits into a new paragraph,
  Shift-Enter inserts a line break), `"hardBreak"` (Enter inserts a `<br>`), or `"swap"`
  (exchange the two). Set it per field (`TipTapWidget(config={"enterKey": "hardBreak"})`) or
  project-wide via `TIPTAP_DEFAULT_CONFIG`. For arbitrary shortcuts, a new **keyboard
  shortcuts** recipe documents registering a high-priority keymap extension.

### Fixed

- **Image-picker overlay no longer trapped behind host modals.** The picker overlay is
  portaled to `<body>` and was fixed at `z-index: 1000`, below common modal stacks
  (Bootstrap 3/4/5 use 1050–1060), so it opened *behind* a host modal the editor was
  embedded in. It now defaults to `z-index: 2000` and is overridable without `!important`
  via the new `--tiptap-modal-z` token (set on `:root`/`html`/`body`, since the
  body-portaled overlay does not inherit from `.django-tiptap`). The in-editor bubble /
  floating / dropdown menus are unaffected — they render inside the editor shell, not on
  `<body>`, so they already stack correctly within a host modal.

## [0.2.0] — 2026-06-21

### Added

- **Theming tiers 2 & 3 — region & shell renderers.** `DjangoTipTap.ui.setRenderer(region, fn)`
  replaces a region — chrome (`"toolbar"` / `"statusbar"`) or a selection-anchored overlay
  (`"bubbleMenu"`, shown over a selection; `"floatingMenu"`, shown on an empty line) — while
  keeping the rest of the editor; `DjangoTipTap.ui.setShellRenderer(fn)` hands over the whole shell
  (the renderer must place the provided `ctx.content` host). Region renderers are **semi-stable**;
  the shell renderer is **experimental**. The bubble/floating menus use a lean built-in positioner
  (no `tippy.js`).
- **Optional JSON storage.** `TipTapJSONField` (a `JSONField`) stores the canonical ProseMirror
  document plus an editor-derived HTML mirror as a `{doc, html}` envelope; its value is a
  `TipTapValue` (`.doc` / `.html`). Render `{{ obj.body }}` server-side with no `|safe` needed.
  Opt in per field, or globally via `TIPTAP_STORAGE_FORMAT="json"` / `TipTapWidget(storage="json")`.
  HTML stays the default. The stored document's link/image protocols are allowlisted in pure
  Python on every save (no new dependency).
- **JSON converters + migration.** `DjangoTipTap.renderHTML(doc)`, `htmlToJSON(html)`, and
  `htmlToStored(html)` convert between HTML and ProseMirror JSON using the bundled schema (no Node,
  no new dependency). In JSON mode the editor falls back to the stored HTML mirror when the `doc`
  is empty, enabling a pure-Python "seed the mirror, convert on first edit" migration. A
  **migrate-into-`TipTapJSONField`** guide (lazy + eager paths) is included.
- **Server-side JSON rendering (Python).** `render_doc(doc)` renders a ProseMirror document to
  safe HTML in pure Python (no Node) — protocol-allowlisted, HTML-escaped, with CSS validation —
  for zero-JS display of programmatically-authored JSON. `TipTapJSONField` uses it to fill a
  missing mirror on save; a `{{ value|tiptap_html }}` template filter is also provided.

## [0.1.0] — 2026-06-20

### Added

- **Django integration**: `TipTapWidget`, `AdminTipTapWidget`,
  `TipTapModelAdminMixin`, and `TipTapFormField`. Stores HTML (render with
  `|safe`); the ProseMirror schema sanitizes on parse (scripts/unknown nodes
  dropped, link/image protocol allowlists).
- **Editor**: full toolbar — formatting, font size/family, text colour,
  highlight, headings, lists, alignment, links, images, tables, and a raw-HTML
  source view — plus a button registry (`ui.registerButton`) and design-token
  theming (`--tiptap-*` / `ui.setTokens`).
- **Images & content**: upload (toolbar/paste/drop, CSRF, protocol-validated)
  with the `{file} → {location}` contract, a library picker, merge tags, an
  `onChange` callback (explicit init / Path B), and `BaseImageUploadView` /
  `ImageUploadError` helpers.
- **Extensibility & i18n**: `registerExtension` (+ `TIPTAP_EXTRA_EXTENSIONS`),
  en/sv locales with `registerLocale`, and re-exported TipTap primitives for
  no-build authoring.
- **Asset modes**: a committed, self-contained bundle (default, node-free) and a
  glue-only ESM build for bring-your-own-TipTap via import maps, with a default
  CDN import map and a startup version-skew check.
- **Settings**: `TIPTAP_DEFAULT_CONFIG`, `TIPTAP_ASSET_MODE`,
  `TIPTAP_IMPORT_MAP`, `TIPTAP_EXTRA_EXTENSIONS`; `{% tiptap_media %}` and
  `{% tiptap_config %}` template tags.
- **Quality**: a TinyMCE-corpus round-trip fidelity test, 100% line+branch
  Python coverage, and full documentation.

[Unreleased]: https://github.com/Artui/django-tiptap-editor/compare/v0.3.1...HEAD
[0.3.1]: https://github.com/Artui/django-tiptap-editor/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/Artui/django-tiptap-editor/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Artui/django-tiptap-editor/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Artui/django-tiptap-editor/compare/v0.0.0...v0.1.0
