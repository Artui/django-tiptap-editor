# django-tiptap-editor

[![CI](https://github.com/Artui/django-tiptap-editor/workflows/tests/badge.svg)](https://github.com/Artui/django-tiptap-editor/actions/workflows/tests.yml)
[![PyPI](https://img.shields.io/pypi/v/django-tiptap-editor.svg)](https://pypi.org/project/django-tiptap-editor/)
[![Python versions](https://img.shields.io/pypi/pyversions/django-tiptap-editor.svg)](https://pypi.org/project/django-tiptap-editor/)
[![Django versions](https://img.shields.io/pypi/djversions/django-tiptap-editor.svg)](https://pypi.org/project/django-tiptap-editor/)
[![License](https://img.shields.io/pypi/l/django-tiptap-editor.svg)](https://github.com/Artui/django-tiptap-editor/blob/main/LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A reusable, pip-installable Django package providing a **drop-in rich-text editor**
backed by [TipTap](https://tiptap.dev) (headless ProseMirror): a form `Widget`, an
admin widget, a `ModelAdmin` mixin, a settings default, and vendored static assets —
**node-free for consumers**.

## What this is

A reusable rich-text editor for Django: a form `Widget`, an admin widget, a
`ModelAdmin` mixin, a settings-driven config, and committed static assets — with a
clean, options-object surface and its own config schema.

- Stored value is **HTML** (render it with `|safe`), never JSON.
- ProseMirror's schema *is* a sanitizer: scripts and unknown nodes are dropped on
  parse, and link/image protocols are allowlisted — so `|safe` is justified.
- **Node-free for consumers**: the editor ships as a committed, self-contained bundle.
  An optional glue-only ESM build lets you bring your own TipTap via CDN / import maps.
- Extensible without a build step: a runtime registry for custom extensions, toolbar
  buttons, and layered (CSS-variable) theming.
- Full toolbar (formatting, font size/family, colour, highlight, lists, alignment,
  links, images, tables, source view), image upload + library picker, merge tags, and
  en/sv i18n out of the box.

## Installation

```bash
pip install django-tiptap-editor
```

Add the app to `INSTALLED_APPS` (it ships the static bundle):

```python
INSTALLED_APPS = [
    # ...
    "django_tiptap_editor",
]
```

## Quickstart

```python
from django import forms
from django_tiptap_editor.forms.fields import TipTapFormField

class ArticleForm(forms.Form):
    body = TipTapFormField()
```

In the admin:

```python
from django.contrib import admin
from django_tiptap_editor.admin.mixin import TipTapModelAdminMixin

@admin.register(Article)
class ArticleAdmin(TipTapModelAdminMixin, admin.ModelAdmin):
    pass  # every TextField becomes a TipTap editor
```

Render the field with `{{ form.media }}` (or `{% tiptap_media %}`) in your template, and
display the stored HTML with `{{ article.body|safe }}`. See the
[documentation](https://artui.github.io/django-tiptap-editor/) for configuration,
the upload/image-list contracts, theming, extension authoring, asset modes, and the
migration guide.

## Documentation

Full documentation is published at
[artui.github.io/django-tiptap-editor](https://artui.github.io/django-tiptap-editor/).

## License

MIT — see [LICENSE](LICENSE).
