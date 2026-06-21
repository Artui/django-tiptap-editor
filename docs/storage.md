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

The `html` mirror is only guaranteed fresh when content is written **through the editor**. If you
mutate `.doc` directly in Python, regenerate the mirror before relying on it — render it in the
browser with the client helper (below), or re-save through a form.

## Settings

| Setting | Default | Effect |
| --- | --- | --- |
| `TIPTAP_STORAGE_FORMAT` | `"html"` | Default storage mode for a `TipTapWidget` when no explicit `storage=` is given. `TipTapJSONField` always uses `"json"`. |

You can also set the mode per widget: `TipTapWidget(storage="json")`.

## Rendering JSON in the browser (SPA / dynamic)

For dynamic display without a server round-trip (or when you store JSON-only and have no mirror),
render the document client-side:

```js
const html = DjangoTipTap.renderHTML(doc); // ProseMirror JSON → HTML string
```

!!! note "Availability"
    `DjangoTipTap.renderHTML` and the HTML↔JSON migration recipe ship in a follow-up
    (TT-10b/TT-10d). This page documents the storage field and the server-side mirror, which are
    available now.

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
