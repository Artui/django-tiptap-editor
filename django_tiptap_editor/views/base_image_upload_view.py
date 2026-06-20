"""Abstract upload endpoint documenting the editor's upload contract."""

from __future__ import annotations

from typing import Any

from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest, JsonResponse
from django.views import View

from django_tiptap_editor.views.image_upload_error import ImageUploadError


class BaseImageUploadView(View):
    """Subclass and implement ``save()`` to wire your own storage.

    Contract (matches ``config.imageUploadUrl``): ``POST`` ``multipart/form-data``
    with a ``file`` field → ``200 {"location": "<url>"}`` on success, or
    ``400 {"error": "<msg>"}`` (no file, or ``save()`` raises ``ImageUploadError``).
    The package owns the contract; the consumer owns storage and access control.
    """

    http_method_names = ["post"]

    def save(self, file: UploadedFile) -> str:
        """Persist ``file`` and return its public URL. Implemented by subclasses."""
        raise NotImplementedError  # pragma: no cover

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        upload = request.FILES.get("file")
        if upload is None:
            return JsonResponse({"error": "No file provided."}, status=400)
        try:
            location = self.save(upload)
        except ImageUploadError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        return JsonResponse({"location": location})
