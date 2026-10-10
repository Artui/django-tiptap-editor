# Security

The editor stores markup and your templates render it, so the boundary matters. The
boundary is **on the server**: everything the package accepts is put through an
allowlist before it is stored, and again when it is displayed.

## Where sanitisation happens

- **HTML storage.** `TipTapFormField` cleans the submitted markup with
  [`sanitize_html`](api.md): anything outside the allowlist is unwrapped, unknown
  attributes are dropped, `script`/`style` bodies are discarded, link and image URLs
  are protocol-allowlisted, and inline styles keep only allowed properties with safe
  values. The allowlist is the field's own: it is built from the field's resolved
  [`features`](configuration.md#restricting-features), so a field whose editor cannot
  make a heading cannot store one either (see [Per field](#per-field)).
- **Display.** The `tiptap_html` filter sanitises again at render time, which is what
  makes it safe on rows stored before this boundary existed.
- **JSON storage.** `TipTapJSONField` protocol-allowlists the `doc` on every save and
  re-derives the `html` mirror from it (`render_doc`); `TipTapValue` sanitises its
  mirror on construction, so no caller can hand a template markup the editor could
  not have produced. `TipTapJSONFormField` also narrows the submitted `doc` to the
  field's features before it is stored.
- **Admin.** `TipTapModelAdminMixin` gives every `TextField` a `TipTapFormField`, unless
  the admin names its own form class for it, so an admin page is cleaned like any other
  form.

The browser-side controls below are still there, and still worth having — they are
what makes the editor *behave* well. They are not the security boundary, because they
run in the browser:

- **ProseMirror's schema is a normalizer.** Content is parsed into a strict document
  model on load; anything the schema doesn't represent — `<script>`, event handlers,
  unknown tags/attributes — is dropped. The editor never *holds* markup it can't model.
- **Link protocols are allowlisted** (`linkProtocols`, default `http`/`https`/`mailto`/
  `tel`) and **image `src` is protocol-validated** on insertion.
- **Source view re-parses through the schema**, so what you see equals what the editor
  submits.

None of that survives a client that skips the editor: the widget is a plain
`<textarea>`, and a direct POST reaches the field with whatever the client chose to
send. That is the case the server-side allowlist exists for.

## What survives

The allowlist is not a second vocabulary maintained beside the editor: it is built
from `EXTENSION_HTML_VOCABULARY`, one entry per built-in extension declaring the tags,
attributes and style properties that extension emits. The same table is where the
built-in extension names come from, so the editor's output and the sanitiser's
allowlist cannot drift apart. The editor's half of that is tested rather than assumed:
`js/test/html-vocabulary.test.ts` renders every attribute the editor's schema defines,
and every case in the fidelity corpus, and fails if anything lands outside this table.

| | Kept |
| --- | --- |
| Blocks | `p`, `h1`–`h6` (with `margin`, `margin-block-end`, `padding-left`, `text-align`), `blockquote`, `pre`/`code`, `hr`, `br`, `ul`, `ol` (`start`, `type`), `li` |
| Inline | `strong`, `em`, `u`, `s`, `code`, `sub`, `sup`, `span` (with `color`, `background-color`, `font-family`, `font-size`) |
| Links | `a` with `href` (allowlisted protocols), `class`, `target` (`_blank`/`_self` only), `rel` (known tokens only), `title` |
| Images | `img` with `src` (allowlisted protocols), `alt`, `title`, `width`, `height`, and layout `style` (`float`, `display`, `vertical-align`, `margin`/`padding` and their per-side forms, `border`, `border-radius`, `width`, `height`) |
| Tables | `table`, `colgroup`, `col`, `tbody`, `tr`, `th`/`td` with `colspan`, `rowspan`, `colwidth`, `background-color`, `text-align` |

Everything else is unwrapped: the tag goes, the text inside it stays. A sanitiser that
deleted what it did not recognise could quietly empty half a document, so it never
deletes visible text — the one exception is `script` and `style`, whose bodies are
code rather than prose and are dropped whole.

### Per field

The table above is what a field configured without `features` keeps. A field with
[`features`](configuration.md#restricting-features) keeps only the vocabularies of its
resolved set (listed features, the always-on core, and their dependencies), plus the
custom extensions its own `extensions` names. What it lacks is not deleted, because the
rule above still holds:

- **A block becomes a paragraph.** `h1`-`h6`, `blockquote`, `pre`, `li`, `td` and `th`
  each keep their text as a paragraph boundary, and the `ul`, `ol` or table structure
  around them is unwrapped. A paragraph the sanitiser opens is never nested inside
  another it opened, and cleaning the result again changes nothing. Nesting the
  submitted markup already had, such as a `<p>` inside a kept `<blockquote>` inside a
  `<p>`, is cleaned as it would be on an unrestricted field rather than repaired.
- **A mark is unwrapped**, as an unknown tag is. A mark that spans a converted block is
  reopened in the paragraph that follows it. One that opens immediately before the block
  is closed there empty, so `<strong><h2>b</h2>c</strong>` on `["bold"]` keeps
  `<strong></strong><p>b</p><strong>c</strong>`; the empty pair holds no text.
- **Attributes and style properties narrow with their feature.** `text-align` goes with
  `textAlign`, `color` with `color`, and so on. The text-style features decorate tags
  other features admit; on their own they admit no tag.

A stored JSON document narrows the same way: a node type the field lacks becomes a
paragraph if it held text, or is replaced by its children, and a mark or attribute the
field lacks is dropped. The `html` mirror rendered from the narrowed document is, for
most content, the markup the HTML path keeps for the same document rendered as HTML. It
differs where a tag is shared between features, because the HTML path judges the tag
and the document path judges the node or mark:

| Field `features` | Content | HTML path keeps | Document path keeps |
| --- | --- | --- | --- |
| `["codeBlock"]` | inline code | `<p><code>b</code></p>` | `<p>b</p>` |
| `["code"]` | a code block | `<p><code>x</code></p>` | `<p>x</p>` |
| `["textStyle"]` | coloured text | `<p><span>a</span></p>` | `<p>a</p>` |
| `["color"]` | text with only a font size | `<p><span>a</span></p>` | `<p>a</p>` |

In each the HTML path keeps a tag the field admits for another feature, emptied of what
the field lacks, and the document path drops the mark that carried it. Neither path keeps
anything the field's allowlist does not.

An image on a field without `image` goes whole on both paths, its `alt` text with it:
the text lives in an attribute, not in content, so there is nothing to unwrap.

### What is not narrowed per field

Narrowing needs the field's config, and only a form field has it. So:

- **Writes that skip the form are not narrowed per field.** A model save through the ORM
  or an API serializer, and `loaddata`, are sanitised as before (against every built-in
  extension on the JSON path, and not at all on a plain `TextField`), whatever the
  editor for that column would allow.
- **The `tiptap_html` filter is not per field.** It has no field to read, so it renders
  against every built-in extension's vocabulary, even when `TIPTAP_DEFAULT_CONFIG` sets
  `features`.
- **Changing a field's `features` does not rewrite stored rows.** A heading saved before
  the field lost `heading` stays in the column until that row is saved again through the
  form.
- **`linkProtocols` is project-wide on the server.** A field's own `linkProtocols` limits
  its editor; the server's allowlist reads the project default.

A link that opens a new browsing context always carries `rel="noopener noreferrer"`,
whatever the stored document asked for: `rel="opener"` re-enables the `window.opener`
handle that `target="_blank"` otherwise implies away.

Content nested deeper than `MAX_DOCUMENT_DEPTH` (100 elements or nodes) is refused
with a `ValidationError` rather than recursed into.

A JSON document is bounded in its values as well as its nodes. Anything nested deeper
than `MAX_JSON_DEPTH` (400 levels, counting every object and array, a node's `attrs`
included) is refused by `TipTapJSONFormField`, and by `TipTapJSONField` on validation
and on save. A document at the node limit reaches about half of that. The bound is for
`json.dumps`, which Django's `JSONField` runs on the value and which recurses once per
level, so it applies where a value is written. A row already stored deeper still
renders, but saving it again raises `ValidationError` until its document is replaced;
`save(update_fields=...)` that leaves the document out still works.

## Rendering

Render with the `tiptap_html` filter, for either storage format:

```django
{% load tiptap %}
{{ article.body|tiptap_html }}
```

`|safe` on an HTML-stored value renders whatever the column happens to hold. For a row
written by this version of the package that is a sanitised value — but for a row
written before it, or by anything other than the form, it is not. `|tiptap_html` costs
one allowlist pass and does not depend on how the row got there.

## Custom extensions

A custom extension emits markup this package has never seen, so declare what it emits.
`TIPTAP_EXTRA_EXTENSIONS` takes either a list of names or a mapping that carries the
vocabulary:

```python
TIPTAP_EXTRA_EXTENSIONS = {
    "callout": {"aside": {"attrs": ["class"], "styles": ["background-color"]}},
    "wordCount": {},  # emits no markup of its own
}
```

A declared vocabulary joins the allowlist and the extension's markup survives intact.
A name given without one (the list form) raises a warning naming the extension, and
its tags are unwrapped — the wrapper is lost, the text is not. Two declarations are
refused outright: a tag that executes script or loads a document (`script`, `style`,
`iframe`, `object`, `embed`, `base`, `meta`, `link`, `form`, `svg`, `template`, …) and
any `on*` attribute.

## JSON storage

[JSON storage](storage.md) (`TipTapJSONField`) keeps the same boundary, with one extra
rule. Because protocol allowlisting happens on *parse* — which a stored-JSON document
never runs — **rendering arbitrary JSON is not automatically safe.** So:

- The field validates the stored `doc` on **every save**: the link/image protocol
  allowlist is enforced in pure Python (no extra dependency), and disallowed
  `javascript:`/`vbscript:`/other schemes on link `href` / image `src` are stripped.
  The canonical value is always safe, whoever wrote it (form, API, import).
- The `html` mirror is **re-derived from the sanitized `doc` on every save** (never
  trusted from the caller) by the built-in **`render_doc`**, which re-applies the
  protocol allowlist, HTML-escapes text and attributes, reduces a link's
  `target`/`rel`, and passes inline `style` values through a conservative CSS allowlist
  (no `;`/`:` injection, no `url(...:...)`, no `expression`). An image's stored `style`
  is split into declarations and filtered against the same layout-property list the
  sanitiser uses. A write can set `{doc, html}` directly (API / import / hand-edit);
  the supplied `html` is discarded, so the rendered surface always reflects only the
  sanitized doc.
- `TipTapValue` sanitises its `html` in `__post_init__`, so the mirror is safe on every
  instance however it was built — including the one a `ModelForm` leaves on
  `form.instance` after validation fails, which is redisplayed straight back to the
  browser.

## Caveats

- **You still control the render context.** The filter trusts the markup it produces;
  keep untrusted input out of attributes you interpolate around it.
- **Content stored before this version was never sanitised.** Rendering it with
  `|tiptap_html` cleans it at display time; see the CHANGELOG for how to clean the
  column itself.
- **Custom extensions widen the surface.** Anything you declare in
  `TIPTAP_EXTRA_EXTENSIONS` is accepted from then on — validate what your extension
  itself accepts.
- **External asset mode** loads TipTap you provide; the browser-side guarantees above
  hold for the pinned, bundled version. See [Asset modes](asset-modes.md). The
  server-side allowlist is unaffected.
- **Uploads are yours to police.** `BaseImageUploadView` enforces the wire contract,
  not file-type/size/virus policy — add those in `save`.
