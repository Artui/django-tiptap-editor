# Asset modes

Two committed build outputs from one source. Pick with `TIPTAP_ASSET_MODE`.

## Bundle (default)

`tiptap.bundle.js` — an IIFE with TipTap + all extensions + the glue inlined. Fully
**node-free**: no build step, no CDN. Emitted by the widget's `class Media` (so
`{{ form.media }}` and the admin work out of the box) and by `{% tiptap_media %}`.

Nothing to configure beyond installing the app.

## External (bring your own TipTap)

`tiptap.glue.esm.js` — the glue only, with `@tiptap/*` left as bare imports resolved by
an **import map**. For consumers who load TipTap from a CDN or their own build.

```python
TIPTAP_ASSET_MODE = "external"
```

```html
{% load tiptap %}
{% tiptap_media %}
```

`{% tiptap_media %}` then emits an `importmap` followed by the glue as
`<script type="module">`. By default the import map pins every required `@tiptap/*`
specifier to the validated version on a CDN (`esm.sh`); override deliberately:

```python
TIPTAP_IMPORT_MAP = {
    "@tiptap/core": "https://esm.sh/@tiptap/core@3.31.4",
    # … or your self-hosted URLs. Set {} to opt out of the default.
}
```

`class Media` always serves the self-contained bundle, so the admin stays node-free even
when external mode is on; external mode applies to templates that use `{% tiptap_media %}`.

### Overriding the map, and self-hosting

`TIPTAP_IMPORT_MAP` replaces the default map rather than adding to it, so an override
must resolve every specifier the glue imports:

```text
@tiptap/core
@tiptap/starter-kit
@tiptap/extension-underline
@tiptap/extension-text-style
@tiptap/extension-font-family
@tiptap/extension-color
@tiptap/extension-text-align
@tiptap/extension-link
@tiptap/extension-image
@tiptap/extension-table
@tiptap/extension-table-row
@tiptap/extension-table-cell
@tiptap/extension-table-header
@tiptap/extension-subscript
@tiptap/extension-superscript
@tiptap/extensions
```

A CDN that rewrites each package's own imports into URLs, as esm.sh does, needs nothing
more. A map pointing at the packages' own `dist/` files does: those import their
dependencies by bare specifier too, so the map must also resolve each of these:

```text
@tiptap/core/jsx-runtime
@tiptap/extension-blockquote
@tiptap/extension-bold
@tiptap/extension-code
@tiptap/extension-code-block
@tiptap/extension-document
@tiptap/extension-hard-break
@tiptap/extension-heading
@tiptap/extension-horizontal-rule
@tiptap/extension-italic
@tiptap/extension-list
@tiptap/extension-paragraph
@tiptap/extension-strike
@tiptap/extension-text
@tiptap/pm/commands
@tiptap/pm/dropcursor
@tiptap/pm/gapcursor
@tiptap/pm/history
@tiptap/pm/keymap
@tiptap/pm/model
@tiptap/pm/schema-list
@tiptap/pm/state
@tiptap/pm/tables
@tiptap/pm/transform
@tiptap/pm/view
linkifyjs
orderedmap
prosemirror-commands
prosemirror-dropcursor
prosemirror-gapcursor
prosemirror-history
prosemirror-keymap
prosemirror-model
prosemirror-schema-list
prosemirror-state
prosemirror-tables
prosemirror-transform
prosemirror-view
rope-sequence
w3c-keyname
```

Both lists are for the validated TipTap version, and `js/test/self-hosted-import-map.test.ts`
regenerates them from the installed packages, so they move when it does.

### Version-skew caveat

The lossless guarantee is validated against the **pinned, bundled** TipTap version. Under
external mode you can load a *different* version, and skew can silently reintroduce
content loss or markup drift. Therefore:

- The glue checks the loaded version at startup and **warns to the console** — louder on a
  major mismatch when you set `window.DJANGO_TIPTAP_TIPTAP_VERSION`. The validated version
  is `DjangoTipTap.supportedTipTapVersion`.
- In external mode **you own re-running the fidelity corpus** against your chosen version.
  The shipped lossless guarantee is for the bundled version only.

The two builds are byte-for-byte identical apart from whether `@tiptap/*` is inlined or
external — the public API, registry, and auto-mount behave the same in both.
