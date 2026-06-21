# Storage format — HTML or JSON

By default the editor stores **HTML**: the widget posts `editor.getHTML()`, you render it with
`|safe`. That's the zero-config path and is right for most Django sites.

Optionally you can store **ProseMirror JSON** instead. JSON is the lossless canonical
representation of the document — better for programmatic transforms, diffing, and feeding a
separate frontend — while still giving you HTML to render server-side.

## Opting in

Use `TipTapJSONField` — a `JSONField` that stores a `{doc, html}` envelope and hands your code a
typed value:

```python
from django.db import models
from django_tiptap_editor.fields import TipTapJSONField

class Article(models.Model):
    body = TipTapJSONField(null=True, blank=True)
```

In a template, render the editor-derived HTML mirror — **no `|safe` needed** (the field marks it
safe; the trust model matches HTML mode — see [Security](security.md)):

```django
{{ article.body }}            {# the HTML mirror #}
{{ article.body.html }}       {# same thing, explicit #}
```

In Python, work with the canonical document:

```python
article.body.doc    # the ProseMirror JSON (dict) — canonical, lossless
article.body.html   # the editor-derived HTML mirror (SafeString)
```

`article.body` is a `TipTapValue` (`.doc` + `.html`). Assign one when writing programmatically:

```python
from django_tiptap_editor import TipTapValue
article.body = TipTapValue.from_stored({"doc": some_doc, "html": "<p>…</p>"})
article.save()
```

## How it works

The editor is the **only authoritative renderer** of the document, so in JSON mode it writes both
sides on every change — `editor.getJSON()` → `doc` and `editor.getHTML()` → `html` — into one
JSON column. Server-side display reads the stored `html`; no JavaScript and no Node are required.

```
edit ──▶ editor ──┬─▶ doc  (canonical, stored)
                  └─▶ html (mirror, stored, rendered with |safe)
```

When you write only the `doc` from Python (no editor involved), the field **renders the mirror
for you on save** with the built-in [server-side renderer](#server-side-rendering-python) — so
`{{ obj.body }}` still works with no JavaScript. An editor-produced `html` is kept as-is (it's the
exact WYSIWYG output); the server renderer only fills a missing mirror.

## Settings

| Setting | Default | Effect |
| --- | --- | --- |
| `TIPTAP_STORAGE_FORMAT` | `"html"` | Default storage mode for a `TipTapWidget` when no explicit `storage=` is given. `TipTapJSONField` always uses `"json"`. |

You can also set the mode per widget: `TipTapWidget(storage="json")`.

## Converting & rendering in the browser

The bundle exposes converters that use the package's exact schema (no Node, no extra
dependency):

```js
DjangoTipTap.renderHTML(doc);     // ProseMirror JSON → HTML string (SPA / dynamic display)
DjangoTipTap.htmlToJSON(html);    // HTML → ProseMirror JSON
DjangoTipTap.htmlToStored(html);  // HTML → { doc, html } envelope (for migration)
```

Use `renderHTML` to display JSON-stored content client-side without a server round-trip, and
`htmlToStored` / `htmlToJSON` to convert existing HTML — see
[Migrating from another editor](recipes/migrating-from-tinymce.md#migrating-into-tiptapjsonfield).

## Server-side rendering (Python)

For zero-JavaScript display of a document the editor never produced (e.g. JSON written by an API
or import), render it in Python with `render_doc`:

```python
from django_tiptap_editor import render_doc

html = render_doc(article.body.doc)   # a safe HTML string
```

It covers the package's node/mark set, applies the link/image protocol allowlist, escapes text,
and validates inline CSS — so the result is safe to render directly. The output is **faithful to,
but not byte-identical with**, the editor's `getHTML()` (the browser normalizes some CSS).
`TipTapJSONField` uses it automatically to fill a missing mirror on save.

A template filter is also available:

```django
{% load tiptap %}
{{ article.body|tiptap_html }}   {# TipTapValue → its mirror; a raw doc dict → render_doc #}
```

## Security

Rendering **arbitrary** stored JSON to HTML is not automatically safe — protocol allowlisting
happens on *parse*, which a stored-JSON path never runs. `TipTapJSONField` therefore validates the
`doc` on every save (the link/image protocol allowlist is enforced in pure Python; disallowed
`javascript:`/`vbscript:` URLs are stripped), so the canonical value is always safe regardless of
who wrote it. See [Security](security.md) for the full boundary.

## Choosing a format

| | HTML (default) | JSON (`TipTapJSONField`) |
| --- | --- | --- |
| Column | `TextField` | `JSONField` |
| Server display | `{{ body|safe }}` | `{{ body }}` (mirror) |
| Programmatic editing | parse HTML | work on `.doc` directly |
| Best for | most Django sites | transforms, diffing, headless/SPA frontends |
