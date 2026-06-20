from __future__ import annotations

import json

from django.core.files.uploadedfile import SimpleUploadedFile, UploadedFile
from django.test import RequestFactory

from django_tiptap_editor.views.base_image_upload_view import BaseImageUploadView
from django_tiptap_editor.views.image_upload_error import ImageUploadError


class OkUploadView(BaseImageUploadView):
    def save(self, file: UploadedFile) -> str:
        return f"/media/{file.name}"


class FailUploadView(BaseImageUploadView):
    def save(self, file: UploadedFile) -> str:
        raise ImageUploadError("File too large.")


rf = RequestFactory()


def test_success_returns_location() -> None:
    request = rf.post(
        "/upload/", {"file": SimpleUploadedFile("a.png", b"x", content_type="image/png")}
    )
    response = OkUploadView.as_view()(request)
    assert response.status_code == 200
    assert json.loads(response.content) == {"location": "/media/a.png"}


def test_missing_file_returns_400() -> None:
    response = OkUploadView.as_view()(rf.post("/upload/"))
    assert response.status_code == 400
    assert "error" in json.loads(response.content)


def test_save_error_returns_400_with_message() -> None:
    request = rf.post(
        "/upload/", {"file": SimpleUploadedFile("a.png", b"x", content_type="image/png")}
    )
    response = FailUploadView.as_view()(request)
    assert response.status_code == 400
    assert json.loads(response.content)["error"] == "File too large."
