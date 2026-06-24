# Quickstart

## A form field

```python
from django import forms
from django_tiptap_editor.forms.fields import TipTapFormField

class ArticleForm(forms.Form):
    body = TipTapFormField()
```

Or attach the widget to any field / model form:

```python
from django import forms
from django_tiptap_editor.widgets.tiptap_widget import TipTapWidget

class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ["title", "body"]
        widgets = {"body": TipTapWidget(config={"height": "400px"})}
```

In the template, include the editor assets and render the form normally:

```html
{{ form.media }}        {# or: {% load tiptap %}{% tiptap_media %} #}
<form method="post">{% csrf_token %}{{ form.as_p }}<button>Save</button></form>
```

The widget renders a `<textarea>`; the editor mounts onto it on load and writes its HTML
back into the textarea on every change, so a normal POST submits HTML.

Display the stored value with `|safe`:

```html
{{ article.body|safe }}
```

## In the admin

```python
from django.contrib import admin
from django_tiptap_editor.admin.mixin import TipTapModelAdminMixin

@admin.register(Article)
class ArticleAdmin(TipTapModelAdminMixin, admin.ModelAdmin):
    pass
```

Every `TextField` becomes a TipTap editor. To limit which fields, set
`tiptap_fields = ["body"]`. The admin always uses the self-contained bundle.

## Dynamic forms (htmx, Turbo, admin inlines)

Auto-mount is **framework-agnostic**: the editor watches the DOM with a
`MutationObserver`, so a widget added after page load mounts automatically no
matter what inserted it — htmx, Turbo, Unpoly, Livewire, Alpine, Django admin
inlines (`formset:added`), or hand-rolled JS. Removing the element tears its
editor down. No per-framework wiring is required. For full control, use
[explicit init (Path B)](api.md#explicit-init-path-b).

**Destructive swaps are supported.** When a form is replaced via an `outerHTML`
swap (e.g. re-rendering with validation errors), the server emits a fresh
`<textarea>` with the same Django `id`. The stale editor is torn down and the new
node is mounted in its place — no duplicate editor, no bare textarea left over, no
orphaned shell.

**Keep `{{ form.media }}` out of the swapped fragment.** Put the editor assets
(`{{ form.media }}` or `{% tiptap_media %}`) in your non-swapped page `<head>`,
never inside a swapped partial. A re-injected `<script>` re-executes the bundle;
the glue guards against this (a second execution is a no-op), but loading the
assets once in the page shell is cleaner and avoids re-downloading them on every
swap.

Next: [Configuration](configuration.md).
