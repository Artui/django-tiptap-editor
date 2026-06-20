"""Django app configuration."""

from __future__ import annotations

from django.apps import AppConfig


class DjangoTipTapEditorConfig(AppConfig):
    name = "django_tiptap_editor"
    verbose_name = "Django TipTap Editor"
    default_auto_field = "django.db.models.BigAutoField"
