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
