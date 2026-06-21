# Recipe: migrating from another editor

Swapping the widget is easy; preserving your existing content is the real work. This
editor stores HTML parsed through a strict ProseMirror schema — anything the schema
doesn't model is normalized away on load. So migration is a **content-validation**
exercise, not an automatic conversion, and there is no promise that behavior is
preserved automatically.

## 1. Swap the widget

Replace your previous widget with `TipTapWidget` (or add `TipTapModelAdminMixin` in the
admin). Both store HTML, so the database column is unchanged.

```python
from django_tiptap_editor.widgets.tiptap_widget import TipTapWidget

class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ["body"]
        widgets = {"body": TipTapWidget()}
```

## 2. Validate your real content first

Before rolling out, run a representative sample of your **production** HTML through the
editor and compare input vs. `getHTML()` output. The package is developed against a
**fidelity corpus** exactly this way — load real HTML, serialize back, and assert no
meaningful loss. Reproduce that over your data:

```js
const editor = DjangoTipTap.init(document.createElement("textarea"), {});
for (const html of yourSamples) {
  editor.commands.setContent(html, false);
  const out = editor.getHTML();
  // diff `html` vs `out` (normalize whitespace) and flag real differences
}
```

## 3. Review the differences

Common, defined normalizations (content preserved, markup tidied):

- `<li>text</li>` → `<li><p>text</p></li>`; tables gain `colgroup`/cell structure.
- `<div>` with no schema node maps to a paragraph.
- Highlight renders as `<span style="background-color">`; colours may use `rgb()`.

Things that genuinely drop unless handled:

- Arbitrary inline CSS the schema doesn't model (exotic block styles, unknown
  properties).
- Editor-specific or legacy markup (`<font>`, conditional comments, Word-paste cruft).
- Tags with no extension (add a [custom extension](../extending.md) if you must keep them).

## 4. Tune and re-run

Add extensions, adjust `config.extensions`, or accept the normalization, then re-run the
validation pass until the diff is only the defined normalizations. For email content, set
inline `margin`/`padding` on paragraphs (preserved) and validate in your target clients.

If you use [external asset mode](../asset-modes.md), re-run this pass against *your*
TipTap version — the shipped fidelity guarantee covers the bundled version only.

## Migrating into `TipTapJSONField`

The steps above keep your HTML column. If you'd rather store the canonical ProseMirror
document (see [Storage format](../storage.md)), migrate the same content into a
`TipTapJSONField`. Conversion runs through the package's exact schema, so it's the same
content-validation exercise — just with a `{doc, html}` envelope as the target.

Add the new field alongside the old column (don't drop the old one until you've verified):

```python
from django_tiptap_editor.fields import TipTapJSONField

class Article(models.Model):
    body = models.TextField()                 # legacy TinyMCE HTML
    body_doc = TipTapJSONField(null=True, blank=True)
```

### Option A — lazy (recommended, no Node/browser job)

Seed each row's **HTML mirror** from the legacy column in a plain data migration (pure
Python — no conversion needed yet), leaving the `doc` empty:

```python
from django.db import migrations

def seed_mirror(apps, schema_editor):
    Article = apps.get_model("yourapp", "Article")
    for row in Article.objects.exclude(body=""):
        row.body_doc = {"doc": {}, "html": row.body}
        row.save(update_fields=["body_doc"])

class Migration(migrations.Migration):
    dependencies = [("yourapp", "0002_article_body_doc")]
    operations = [migrations.RunPython(seed_mirror, migrations.RunPython.noop)]
```

Now:

- **Display works immediately** — `{{ article.body_doc }}` renders the mirror (your legacy
  HTML), no `|safe` needed.
- **Editing converts faithfully** — when a record is opened, the editor hydrates from the
  mirror (the schema parses it, exactly like HTML mode), and the first save writes a real
  `{doc, html}` envelope. Content normalizes to the schema as records are edited.

The trade-off: an un-edited row has an **empty `.doc`** until its first save (its `.html`
mirror is the legacy content). If you need a populated `.doc` for every row right away,
use Option B.

### Option B — eager (convert every row up front)

Faithful HTML→JSON conversion needs the package's schema, which lives in the committed
browser bundle, so a one-time bulk conversion runs that bundle in a browser via
`DjangoTipTap.htmlToStored(html)` (it returns the `{doc, html}` envelope). Load the bundle
on a throwaway page (or drive it with a headless browser), then convert rows fetched from a
small endpoint:

```js
// runs where tiptap.bundle.js is loaded
for (const row of rowsToConvert) {            // [{id, html}, …] from your API
  const envelope = DjangoTipTap.htmlToStored(row.html);
  await fetch(`/admin-convert/${row.id}/`, {  // your endpoint: save envelope to body_doc
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
    body: JSON.stringify(envelope),
  });
}
```

The companion converters `DjangoTipTap.htmlToJSON(html)` and `DjangoTipTap.renderHTML(doc)`
are available for custom pipelines.

### Validate first, either way

Before migrating for real, run a representative sample through `htmlToStored` and compare
`envelope.html` against your originals (normalize whitespace) — the same content-validation
pass as step 2, now landing in JSON. The defined normalizations in step 3 apply identically;
the [security boundary](../security.md#json-storage) (render-time protocol allowlisting)
covers the stored document.
