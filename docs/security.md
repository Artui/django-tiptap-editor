# Security

The editor stores markup and your templates render it, so the boundary matters. The
boundary is **on the server**: everything the package accepts is put through an
allowlist before it is stored, and again when it is displayed.

## Where sanitisation happens

- **HTML storage.** `TipTapFormField` cleans the submitted markup with
  [`sanitize_html`](api.md): anything outside the allowlist is unwrapped, unknown
  attributes are dropped, `script`/`style` bodies are discarded, link and image URLs
  are protocol-allowlisted, and inline styles keep only allowed properties with safe
  values.
- **Display.** The `tiptap_html` filter sanitises again at render time, which is what
  makes it safe on rows stored before this boundary existed.
- **JSON storage.** `TipTapJSONField` protocol-allowlists the `doc` on every save and
  re-derives the `html` mirror from it (`render_doc`); `TipTapValue` sanitises its
  mirror on construction, so no caller can hand a template markup the editor could
  not have produced.

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
allowlist cannot drift apart.

| | Kept |
| --- | --- |
| Blocks | `p`, `h1`–`h6` (with `margin`, `margin-block-end`, `padding-left`, `text-align`), `blockquote`, `pre`/`code`, `hr`, `br`, `ul`, `ol` (`start`, `type`), `li` |
| Inline | `strong`, `em`, `u`, `s`, `code`, `sub`, `sup`, `span` (with `color`, `background-color`, `font-family`, `font-size`) |
| Links | `a` with `href` (allowlisted protocols), `class`, `target` (`_blank`/`_self` only), `rel` (known tokens only) |
| Images | `img` with `src` (allowlisted protocols), `alt`, `title`, `width`, `height`, and layout `style` (`float`, `display`, `vertical-align`, `margin`/`padding` and their per-side forms, `border`, `border-radius`, `width`, `height`) |
| Tables | `table`, `colgroup`, `col`, `tbody`, `tr`, `th`/`td` with `colspan`, `rowspan`, `colwidth`, `background-color` |

Everything else is unwrapped: the tag goes, the text inside it stays. A sanitiser that
deleted what it did not recognise could quietly empty half a document, so it never
deletes visible text — the one exception is `script` and `style`, whose bodies are
code rather than prose and are dropped whole.

A link that opens a new browsing context always carries `rel="noopener noreferrer"`,
whatever the stored document asked for: `rel="opener"` re-enables the `window.opener`
handle that `target="_blank"` otherwise implies away.

Content nested deeper than `MAX_DOCUMENT_DEPTH` (100 elements or nodes) is refused
with a `ValidationError` rather than recursed into.

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
