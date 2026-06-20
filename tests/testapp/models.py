from __future__ import annotations

from django.db import models


class Article(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()
    summary = models.TextField(blank=True)

    class Meta:
        app_label = "testapp"
