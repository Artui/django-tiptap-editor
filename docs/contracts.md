# Client contracts

The package owns the editor; you own your domain. Image upload and the image library
use small, conventional HTTP contracts — wire them to your own storage and access
control.

## Upload (`imageUploadUrl`)

The editor `POST`s `multipart/form-data` with a single field named `file` (and an
`X-CSRFToken` header from the `csrftoken` cookie):

- **200** → `{"location": "<url>"}` — inserted as the image `src`.
- **400** → `{"error": "<message>"}` — surfaced to the console.

`BaseImageUploadView` implements the contract; you implement `save`:

```python
from django.core.files.storage import default_storage
from django_tiptap_editor.views.base_image_upload_view import BaseImageUploadView
from django_tiptap_editor.views.image_upload_error import ImageUploadError

class ImageUploadView(BaseImageUploadView):
    def save(self, file):
        if file.size > 5 * 1024 * 1024:
            raise ImageUploadError("File too large (max 5 MB).")
        name = default_storage.save(f"uploads/{file.name}", file)
        return default_storage.url(name)
```

```python
# urls.py
path("editor/upload/", ImageUploadView.as_view(), name="tiptap-upload"),
```

```python
TipTapWidget(config={"imageUploadUrl": "/editor/upload/"})
```

The view inherits Django's CSRF protection; the editor sends the token automatically.
Apply your own auth (e.g. `LoginRequiredMixin`).

## Image list (`imageListUrl`)

The library picker `GET`s the URL and expects a JSON array:

```json
[{"title": "Logo", "value": "https://cdn.example/logo.png"}]
```

`value` becomes the image `src` (protocol-validated). Build it from your media library
in any view that returns `JsonResponse`.

## Preview

There is no preview endpoint — render previews client-side from the `onChange` callback.
See [the preview recipe](recipes/preview.md).

## Security

Every inserted `src` (upload `location` and picker `value`) is protocol-validated
(`http`/`https`/`data`; `javascript:` rejected). See [Security](security.md).
