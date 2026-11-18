# Recipe: live preview

There is no server-side preview endpoint — render previews on the client from the
`onChange` callback (available via [explicit init](../api.md#explicit-init-path-b)).

```html
<textarea id="ed"></textarea>
<div id="preview" class="prose"></div>

<script>
  const preview = document.getElementById("preview");
  DjangoTipTap.init(document.getElementById("ed"), {
    onChange(html) {
      preview.innerHTML = html;  // editor output is schema-sanitized
    },
  });
</script>
```

The editor's output is already constrained by the schema (see [Security](../security.md)),
so it is safe to drop into a preview node. For an email-style preview, render `html` into
an iframe with your email CSS instead of a `<div>`.

Because `onChange` is a JS function it can't travel through the `data-tiptap-config`
attribute used by auto-mount — use `init()` (Path B) when you need it. An auto-mounted
field fires `input` on its bound textarea instead (see
[Events on the bound textarea](../api.md#events-on-the-bound-textarea)); in HTML storage
the textarea's value is the HTML to preview:

```js
const field = document.getElementById("id_body");
field.addEventListener("input", () => {
  preview.innerHTML = field.value;
});
```

In JSON storage the value is the `{doc, html}` envelope, so preview `JSON.parse(field.value).html`.
