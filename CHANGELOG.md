# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Images resize by dragging their corners.** Selecting an image in the editor
  body now shows four corner handles; dragging one sets the width and height the
  document asks for, preserving the aspect ratio and clamping to the editor's
  own width. Set `imageResize: False` to pin images to their inserted size.

  This is a display size, not a re-encode: the uploaded file is untouched and
  keeps its own resolution. The size is committed as the unitless `width` /
  `height` attributes the corpus already uses, so it survives both storage
  formats, and the whole drag lands as one transaction -- one undo step, not one
  per pixel. Legacy content whose size lives in `style="width: 500px"` has those
  declarations cleared on resize (`float` and `margin` are kept), since a style
  width would otherwise outrank the attribute and the drag would appear to do
  nothing.

  The handles are an overlay that tracks the selected image, not a wrapper
  around it. That is deliberate: the caret's height is taken from the box beside
  it, so a bare `<img>` -- an inline replaced element -- gets a caret spanning
  the image, while a wrapper drops it to a text-height stub. Leaving the image
  node's own DOM untouched keeps the caret, the line box and the serialized
  value identical whether resizing is on or off.

### Fixed

- **Server-rendered images no longer carry an invalid CSS length.** `render_doc`
  emitted a resized image as `width="300" style="width: 300"`, and a bare number
  is not a CSS length, so every browser discarded that declaration -- the
  attribute had been doing the work alone. The style is now emitted only for
  values that carry a unit (`50%`, `300px`), which the attribute cannot express
  on its own. Resizing makes this path hot, which is what surfaced it.

- **Optional native color picker on the text-color and highlight dropdowns.**
  Both dropdowns offered a fixed swatch grid and nothing else, so any color
  outside the configured palette was unreachable from the toolbar. Setting
  `colorPicker: True` appends a native `<input type="color">` under both grids,
  seeded from the current color. Off by default, because the swatch grid alone
  is what keeps a document's colors to a house palette.

  The picker commits on `change` rather than `input`, so dragging through the
  OS color wheel produces one undo step instead of one per intermediate shade.
  Values in a notation the native control can't take (`rgb()`, a named color)
  leave it on black rather than showing a wrong color.

## [0.8.0] — 2026-08-14

### Fixed

- **Enter inside a list now starts the next item under every `enterKey` mode.**
  With `enterKey` set to `"hardBreak"` or `"swap"`, the high-priority Enter
  binding applied inside list items too: pressing Enter in a bullet appended a
  `<br>` to the same `<li>` instead of creating the next one. There was no
  keyboard route to a second bullet — and none out of the list either, since the
  empty-item Enter that normally lifts out was swallowed the same way. The two
  handlers now decline the key inside a list item, which hands it to the list
  keymap that splits the item and lifts out of an empty one. `"swap"` also no
  longer nests a second `<p>` inside one bullet on Shift-Enter. The default
  `"paragraph"` mode was never affected.

  Documented as a rule rather than an accident: `enterKey` configures behaviour
  *outside* lists; inside a list item Enter starts the next item and Shift-Enter
  breaks the line.

### Added

- **`harness/`** — a no-build page (`make harness`) that mounts real editors the
  way the widget does and replays scripted key presses across all three
  `enterKey` modes, asserting the serialized HTML. The manual mirror of
  `js/test/enter-key.test.ts`.

### Security

- **`linkify-it` → 5.0.2 and `postcss` → 8.5.26** (both HIGH), plus
  **`pymdown-extensions` → 11.0.1** (MEDIUM). All three open advisories closed.

  **None of them reached consumers**, and the distinction is worth stating
  rather than implying. `linkify-it` arrives via `markdown-it` →
  `prosemirror-markdown` → `@tiptap/pm`, and **`markdown-it` is not in the
  shipped bundle at all** — the `linkify` strings in `tiptap.bundle.js` belong
  to `linkifyjs`, a different package. `postcss` is vite's, and
  `pymdown-extensions` is docs-only. The committed bundles are **byte-identical**
  after the upgrade, which is the evidence: had any of this been shipped, the
  rebuild would have changed them.

- **Tested against Django 6.1.** Django 6.1 removed
  `django.utils.cache.cc_delim_re`, which DRF 3.17.x imports at module level, so
  that pairing fails at `import rest_framework`.

## [0.7.0] — 2026-07-02

### Security

- **Fixed a `javascript:` scheme-allowlist bypass in the JSON-storage sanitizer.**
  `sanitize_doc` (and `render_doc` / the `tiptap_html` filter that build on it)
  detected a URL's scheme without stripping the ASCII whitespace and C0/DEL
  control characters a browser removes while resolving a URL. A stored `href` /
  image `src` such as `java\nscript:alert(1)`, `java\tscript:…`, or
  `\x01javascript:…` therefore slipped past the link/image protocol allowlist and
  executed on click. Whitespace and control characters are now removed before
  scheme detection, so these values are correctly dropped. Affects stored-JSON
  (`TipTapJSONField`) documents written outside the editor (API / import /
  hand-edit) since JSON storage was introduced in 0.2.0; HTML-mode storage and
  the editor-side JS path were unaffected.
- **The `TipTapJSONField` HTML mirror is now always re-derived from the sanitized
  `doc` on save**, never trusted from the caller. Previously a direct write of a
  `{doc, html}` envelope (API / import / hand-edit) kept a caller-supplied `html`
  verbatim when non-empty, so a benign `doc` could ship hostile markup through the
  rendered mirror. The mirror now reflects only the sanitized doc.

### Changed

- `TipTapModelAdminMixin` now also swaps the admin editor onto `TipTapJSONField`
  columns (in JSON storage mode), not just `TextField`s — so JSON-stored fields
  get the admin-tuned widget out of the box.

### Docs

- Corrected the "stores HTML, never JSON" claim in the README and docs to note
  the optional `TipTapJSONField` JSON storage, and updated the storage/security
  docs to describe the always-re-derived HTML mirror.

## [0.6.0] — 2026-07-01

### Added

- **Configurable text-color / highlight palettes.** Two new config keys —
  `textColors` and `highlightColors` (each a list of CSS colors) — override the
  swatches shown in the `color` (text) / `highlight` (background) toolbar
  dropdowns, per field or via `TIPTAP_DEFAULT_CONFIG`. Omit them to keep the
  built-in palettes (no change for existing consumers). Like the font lists,
  the swatches resolve per editor at render time; invalid values fail loudly via
  `validate_config`.

## [0.5.0] — 2026-07-01

### Added

- **Configurable font-family / font-size dropdowns.** Two new config keys —
  `fontFamilies` (a list of CSS font stacks) and `fontSizes` (a list of CSS
  lengths like `"16px"`) — override the presets shown in the `fontFamily` /
  `fontSize` toolbar dropdowns, per field or via `TIPTAP_DEFAULT_CONFIG`. Omit
  them to keep the built-in lists (no change for existing consumers). The lists
  resolve per editor at render time; invalid values (e.g. a string instead of a
  list of strings) fail loudly via `validate_config`.

## [0.4.0] — 2026-06-25

### Added

- **`manualMount` opt-out is now live.** Setting `manualMount: true` on a field (per widget
  or via `TIPTAP_DEFAULT_CONFIG`) makes the *automatic* triggers — the initial scan and the
  `MutationObserver` — skip it, so it never mounts before your renderers/extensions are
  registered. Mount it yourself afterwards with `DjangoTipTap.autoMount()` (which mounts every
  field, including `manualMount` ones) or `DjangoTipTap.init(el, config)`. The key was already
  accepted and serialized by the Python side; this wires it into the JS mount path.

### Fixed

- **htmx history (Back/Forward) restores a live editor.** With `hx-boost` / `hx-push-url` /
  `hx-history`, htmx caches a static snapshot of the page — capturing both the rendered shell
  and the hidden, already-bound textarea — and restores it on Back (firing
  `htmx:historyRestore`, not `afterSwap`). The restored field used to stay a frozen, dead shell
  because mount idempotency trusted the serialized `data-tiptap-bound` attribute. Idempotency
  now lives in the live editor map, so the restored field re-mounts a working editor and the
  dead snapshot shell is removed. Consumers can still set `hx-history="false"` to skip the
  snapshot entirely.
- **Morphing swaps no longer un-hide the raw textarea.** A morph (`hx-swap="morph"` /
  idiomorph) reconciles the live textarea's attributes back to the server markup, stripping
  `display:none` and `data-tiptap-bound` and exposing the raw field next to the editor. A
  narrow per-editor attribute observer now re-asserts the hidden state in place (no remount,
  no global attribute observation). Mark the editor region `hx-preserve` for pure-attribute
  morphs.

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

[Unreleased]: https://github.com/Artui/django-tiptap-editor/compare/v0.8.0...HEAD
[0.8.0]: https://github.com/Artui/django-tiptap-editor/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/Artui/django-tiptap-editor/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/Artui/django-tiptap-editor/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/Artui/django-tiptap-editor/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/Artui/django-tiptap-editor/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/Artui/django-tiptap-editor/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/Artui/django-tiptap-editor/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Artui/django-tiptap-editor/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Artui/django-tiptap-editor/compare/v0.0.0...v0.1.0
