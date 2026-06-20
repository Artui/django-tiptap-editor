# Installation

```bash
pip install django-tiptap-editor
```

Add the app to `INSTALLED_APPS` — it ships the committed JS/CSS bundle as static files:

```python
INSTALLED_APPS = [
    # ...
    "django.contrib.staticfiles",
    "django_tiptap_editor",
]
```

Run `collectstatic` for production as usual:

```bash
python manage.py collectstatic
```

That's all that's required for the default (bundle) asset mode — there is **no Node
dependency** in your project. To bring your own TipTap from a CDN instead, see
[Asset modes](asset-modes.md).

## Requirements

| | Minimum | Tested |
| --- | --- | --- |
| Python | 3.10 | 3.10 – 3.14 |
| Django | 4.2 | 4.2, 5.0, 5.1, 5.2, 6.0 |

The editor stores **HTML**; render it with `|safe` (see [Security](security.md) for why
that is justified).
