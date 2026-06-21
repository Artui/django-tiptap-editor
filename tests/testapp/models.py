from __future__ import annotations

from django.db import models

from django_tiptap_editor.fields.tiptap_json_field import TipTapJSONField


class Article(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()
    summary = models.TextField(blank=True)
    document = TipTapJSONField(null=True, blank=True)

    class Meta:
        app_label = "testapp"
