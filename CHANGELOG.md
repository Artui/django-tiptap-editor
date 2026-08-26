# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.10.0] — 2026-08-26

### Upgrade note — content is now sanitised on the server

**What changes.** Until now nothing on the server inspected what a project stored.
The editor's schema drops scripts and unknown tags, but it runs in the browser, and
the widget is a plain `<textarea>`: a client that never loads the editor posted
whatever it liked, and the docs told you to render it with `|safe`. That is fixed.

- Submitted HTML is put through an allowlist when the form cleans it
  (`TipTapFormField`), and again when it is displayed (`{{ value|tiptap_html }}`).
- The allowlist is built from the extensions the editor mounts, so markup the editor
  produces round-trips byte-identically. Anything else has its tag unwrapped and keeps
  its text; `script` and `style` bodies are dropped whole.
- `TipTapValue` sanitises its `html` mirror on construction, so a value is safe to
  render however it was built — including the one a `ModelForm` leaves on
  `form.instance` after validation fails.
- A `<a target="_blank">` always carries `rel="noopener noreferrer"`, whatever the
  stored document asked for.
- No new dependency: the package still requires only `django>=4.2`.

**What to check before upgrading.**

1. **Custom extensions.** If you set `TIPTAP_EXTRA_EXTENSIONS`, declare what each
   extension emits, or its markup is unwrapped on the next save. The list form still
   works and now warns, naming the extension:

   ```python
   TIPTAP_EXTRA_EXTENSIONS = {
       "callout": {"aside": {"attrs": ["class"], "styles": ["background-color"]}},
       "shortcuts": {},  # emits no markup of its own
   }
   ```

2. **Templates.** Swap `{{ article.body|safe }}` for
   `{% load tiptap %}{{ article.body|tiptap_html }}`. `|safe` still renders whatever
   the column holds; the filter sanitises it first, which is what makes it right for
   rows written before this release.

3. **Anything that writes the JSON field directly.** Values that used to become an
   empty document now raise `ValidationError`: assigning a string, a list, or any
   non-mapping to a `TipTapJSONField`, and posting `[]` / `"oops"` / `42` to
   `TipTapJSONFormField`. If you were relying on the old coercion, you were storing
   empty documents.

4. **Very deeply nested content.** Documents and markup nested deeper than 100 levels
   are refused with a `ValidationError` instead of raising `RecursionError` out of a
   save.

**Content already stored.** Nothing is rewritten in place — existing rows keep exactly
the bytes they have. Rendering them with `|tiptap_html` cleans them at display time.
To clean the column itself, run the sanitiser over it in a data migration:

```python
from django_tiptap_editor import sanitize_html

for article in Article.objects.all().iterator():
    cleaned = str(sanitize_html(article.body))
    if cleaned != article.body:
        article.body = cleaned
        article.save(update_fields=["body"])
```

JSON-stored rows are re-derived from their sanitised `doc` on their next save, as
before.

### Added

- **`sanitize_html`** — an allowlist HTML sanitiser in pure Python, exported from the
  package root. Unknown tags are unwrapped rather than deleted, so no pass can quietly
  empty a document; `script` and `style` bodies are the exception and are dropped
  whole. Link and image URLs are protocol-allowlisted, inline styles keep only allowed
  properties with values that pass the same conservative CSS gate the JSON renderer
  uses, and character references are re-emitted as written so an author's `&nbsp;`
  survives a save.
- **`get_html_schema` / `HtmlSchema`** — the allowlist itself, built from
  `EXTENSION_HTML_VOCABULARY`: one entry per built-in extension declaring the tags,
  attributes and style properties it emits. `BUILTIN_EXTENSIONS` is derived from that
  table's keys, so the names the editor knows and the markup the server accepts come
  from one place and cannot drift apart.
- **`TIPTAP_EXTRA_EXTENSIONS` accepts a vocabulary.** A mapping of extension name to
  `{tag: {"attrs": [...], "styles": [...]}}` joins the allowlist, so a custom node's
  markup survives sanitisation. A tag that executes script or loads a document, and
  any `on*` attribute, are refused with `ImproperlyConfigured`.
- **`tiptap_html` renders a stored HTML string**, not only a `TipTapValue` or a bare
  doc — one filter for both storage formats, and the display-time boundary for content
  stored before this release.

### Fixed

- **A JSON string assigned to `TipTapJSONField` is parsed instead of refused.**
  `models.JSONField` defines no `to_python`, so this field's `super()` call was
  `Field.to_python` -- a no-op that handed the string on unparsed. A value from a
  fixture or a deserializer became an empty document without a word.

- **A row seeded by the HTML-to-JSON migration survives its next save.** The
  documented recipe seeds rows as `{"doc": {}, "html": "<p>legacy</p>"}`, and the
  stored mirror was unconditionally re-derived from the doc -- which, for an empty
  doc, renders `""`. Every migrated row was blanked the next time it was saved. The
  seeded mirror is now kept when the doc has no content, and it is still sanitised,
  because the value runs its HTML through the allowlist on construction.

- **Stored XSS on the HTML path.** `TipTapFormField` accepted the POST body verbatim:
  a plain `forms.Form` fed `<img src=x onerror=…>` reported success and handed that
  string back on `cleaned_data`, and the docs said to render it with `|safe`. The field
  now sanitises in `to_python`, so length validation counts what will be stored and the
  value a view saves is already reduced to markup the editor could have produced.
- **Stored XSS on the JSON path without a model.** A plain `forms.Form` with
  `TipTapJSONFormField` put the client's `html` on `cleaned_data` as a `SafeString`:
  the mirror was only re-derived at the ORM boundary, so any preview, wizard or
  non-`ModelForm` handler rendered attacker markup. The form field now validates the
  envelope, protocol-allowlists the `doc`, and re-derives the mirror from it.
- **`TipTapValue.from_stored` marked caller-supplied HTML safe.** The mirror is now
  sanitised in `__post_init__`, so the invariant holds for every instance rather than
  for values that happen to have made a database round trip.
- **`tiptap_html` returned a `TipTapValue`'s mirror verbatim** while rendering a bare
  doc safely. Both branches now end at the same guarantee.
- **Assigning a non-mapping to a `TipTapJSONField` persisted an empty document.**
  A string, a list or a number silently emptied the row; the migration case the docs
  describe (copying a legacy HTML column across) would have emptied every row with no
  error. `from_stored` now raises `ValidationError` and says what the value should have
  been.
- **`'[]'`, `'"oops"'` and `42` cleaned successfully into an empty document** through
  `TipTapJSONFormField`. They are field errors now: a form that reports success while
  discarding the submission is worse than one that refuses it.
- **Unbounded document nesting.** A few kilobytes of nesting validated fine and then
  raised `RecursionError` out of `get_prep_value` — a 500, not a field error. Both the
  document walker and the HTML sanitiser now refuse content deeper than
  `MAX_DOCUMENT_DEPTH`.
- **Link `rel` and `target` were emitted from the document with no allowlist**, so a
  stored `rel="opener"` re-enabled the `window.opener` handle `target="_blank"` implies
  away. `target` is restricted to `_blank`/`_self`, `rel` to known-safe tokens, and
  `_blank` always carries `noopener noreferrer`.
- **`TipTapWidget`'s docstring described a config precedence no subclass follows** —
  it claimed subclass overrides win over a per-instance `config=`, while
  `AdminTipTapWidget` (and its own docstring) do the opposite.
- **`docs/security.md` argued for `|safe` from browser-side controls alone** and its
  Caveats section never mentioned that a direct POST bypasses every one of them. The
  page now describes where sanitisation actually happens and enumerates what survives.


- **`TipTapJSONField` works in a `ModelForm`, `full_clean()` and the admin.** The
  field had no `validate()`, so Django's `JSONField.validate` ran `json.dumps()`
  over the `TipTapValue` the field hands back -- a dataclass, not JSON -- and
  every non-empty document failed with "Value must be valid JSON". The plain ORM
  path accepted the identical value, so the two entry points disagreed
  completely and the field did not work in either of its most common
  deployments. Validation now checks the `{doc, html}` mapping that actually
  reaches the column, which keeps the JSON contract honest (a document carrying
  something unserializable is still a validation error) while letting the real
  Django paths through.

- **Submitting with the source view open saves what the source view shows.**
  Nothing flushed the raw-HTML textarea back into the form field, and the two
  storage modes failed in opposite directions: HTML storage copied raw mid-edit
  markup into the field on every keystroke, so a submit persisted markup the
  schema would have dropped, while JSON storage copied nothing at all, so the
  edit was silently lost. Both are the same defect -- the bound field held
  something other than what the schema produces. Submitting now re-parses the
  source through the schema first, exactly as closing the source view does, and
  closes the view so the author sees the normalized result. The flush is wired
  to `submit` (native and `requestSubmit()`) and to `formdata` (the ajax
  submissions that build a `FormData` from the form), and the per-keystroke raw
  sync is gone: the field only ever carries a schema-produced value in its
  storage format.

- **A `tiptap_fields` entry that matches nothing is a system-check error.**
  `TipTapModelAdminMixin` silently ignored a name that is not a field on the
  model, or one naming a field the widget cannot apply to: the admin just
  rendered a plain textarea and nothing said why. Such an entry is now reported
  by Django's check framework at startup (`django_tiptap_editor.E002` and
  `E003`). A bare string other than `"__all__"` is reported too
  (`django_tiptap_editor.E001`) -- it was matched with `in`, i.e. a substring
  test, so `"somebody"` quietly turned `body` into an editor.

### Changed

- Text and attribute values rendered by `render_doc` escape `&`, `<`, `>` and (in
  attributes) `"`, rather than also rewriting `'` to `&#x27;`. Escaping exactly what a
  browser's own serialiser escapes is what lets a document round-trip through the
  sanitiser unchanged; an apostrophe is inert in text and inside a double-quoted
  attribute either way.
- `get_extra_extensions()` returns a mapping of name to declared vocabulary (`None`
  when undeclared) rather than a `frozenset` of names.

- **`TipTapJSONField` validates a document's node and mark vocabulary.** Nothing
  checked a stored document's `type` names against anything. The only vocabulary
  that existed at rest was the server-side renderer's dispatch, which keeps an
  unknown node's children and drops the wrapper -- so because the `html` mirror
  is re-derived from the `doc` on every save, a custom node registered by the
  documented extension recipe round-tripped in the editor and was flattened out
  of the stored mirror on the first save, silently. `full_clean()`, a
  `ModelForm` and the admin now reject a document whose node or mark types the
  mirror cannot render. Types your own extensions add are declared in
  `TIPTAP_EXTRA_EXTENSIONS`, which already declares extension names for config
  validation; declaring one means the `doc` keeps it and the derived mirror
  still cannot represent it, so render those documents from `doc`. Documents the
  editor itself produces are unaffected. Writes through the plain ORM are not
  validated, as everywhere else in Django.

### Docs

- Extending: a section on custom nodes under JSON storage -- what
  `TIPTAP_EXTRA_EXTENSIONS` now declares, and why a declared type still has to
  be rendered from `doc` rather than from the `html` mirror.


## [0.9.0] — 2026-08-18

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

### Fixed

- **Server-rendered images keep their layout styling.** `render_doc` never read an
  image's stored `style`, so under JSON storage an image carrying
  `style="float: right; margin: 8px"` rendered with the float and margins
  silently dropped -- while the same document stored as HTML kept them. One
  document, two renderings, depending only on the storage format. The editor
  round-trips that attribute deliberately (the fidelity corpus depends on it),
  and this path now does too.

  The style is not passed through raw: it is split into declarations and each
  one filtered, keeping only layout properties (`float`, `display`,
  `vertical-align`, `margin`/`padding` and their per-side forms, `border`,
  `border-radius`, `width`, `height`) with every value still passing the
  existing conservative CSS allowlist -- so nothing carrying its own `;` or `:`
  survives, and `render_doc` output stays safe to mark safe. Where a style
  width or height meets a `width`/`height` attribute, the attribute wins, since
  a style declaration would otherwise outrank the size the editor writes.

- **Server-rendered images no longer carry an invalid CSS length.** `render_doc`
  emitted a resized image as `width="300" style="width: 300"`, and a bare number
  is not a CSS length, so every browser discarded that declaration -- the
  attribute had been doing the work alone. The style is now emitted only for
  values that carry a unit (`50%`, `300px`), which the attribute cannot express
  on its own. Resizing makes this path hot, which is what surfaced it.

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

[Unreleased]: https://github.com/Artui/django-tiptap-editor/compare/v0.10.0...HEAD
[0.10.0]: https://github.com/Artui/django-tiptap-editor/compare/v0.9.0...v0.10.0
[0.9.0]: https://github.com/Artui/django-tiptap-editor/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/Artui/django-tiptap-editor/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/Artui/django-tiptap-editor/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/Artui/django-tiptap-editor/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/Artui/django-tiptap-editor/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/Artui/django-tiptap-editor/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/Artui/django-tiptap-editor/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/Artui/django-tiptap-editor/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Artui/django-tiptap-editor/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Artui/django-tiptap-editor/compare/v0.0.0...v0.1.0
