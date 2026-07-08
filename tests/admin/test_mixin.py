from __future__ import annotations

from typing import Any

from django.db import models

from django_tiptap_editor.admin.mixin import TipTapModelAdminMixin
from django_tiptap_editor.constants import STORAGE_FORMAT_JSON
from django_tiptap_editor.widgets.admin_tiptap import AdminTipTapWidget
from tests.testapp.models import Article


class FakeModelAdmin:
    """Stand-in for admin.ModelAdmin — captures the kwargs the mixin passes up."""

    def formfield_for_dbfield(
        self, db_field: models.Field, request: Any, **kwargs: Any
    ) -> dict[str, Any]:
        return kwargs


def _field(name: str) -> models.Field:
    return Article._meta.get_field(name)


def test_all_applies_widget_to_textfield() -> None:
    class A(TipTapModelAdminMixin, FakeModelAdmin):
        pass

    kwargs = A().formfield_for_dbfield(_field("body"), None)
    assert kwargs["widget"] is AdminTipTapWidget


def test_charfield_left_untouched() -> None:
    class A(TipTapModelAdminMixin, FakeModelAdmin):
        pass

    assert "widget" not in A().formfield_for_dbfield(_field("title"), None)


def test_explicit_list_includes_named_field() -> None:
    class A(TipTapModelAdminMixin, FakeModelAdmin):
        tiptap_fields = ["body"]

    kwargs = A().formfield_for_dbfield(_field("body"), None)
    assert kwargs["widget"] is AdminTipTapWidget


def test_explicit_list_excludes_other_textfield() -> None:
    class A(TipTapModelAdminMixin, FakeModelAdmin):
        tiptap_fields = ["body"]

    assert "widget" not in A().formfield_for_dbfield(_field("summary"), None)


def test_json_field_gets_admin_widget_in_json_storage_mode() -> None:
    class A(TipTapModelAdminMixin, FakeModelAdmin):
        pass

    widget = A().formfield_for_dbfield(_field("document"), None)["widget"]
    # An instance (pinned to JSON storage), not the bare class.
    assert isinstance(widget, AdminTipTapWidget)
    assert widget.storage == STORAGE_FORMAT_JSON


def test_json_field_excluded_when_not_listed() -> None:
    class A(TipTapModelAdminMixin, FakeModelAdmin):
        tiptap_fields = ["body"]

    assert "widget" not in A().formfield_for_dbfield(_field("document"), None)
