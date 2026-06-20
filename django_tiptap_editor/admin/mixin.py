"""ModelAdmin mixin that swaps the admin TipTap widget onto text fields."""

from __future__ import annotations

from typing import Any

from django.db import models

from django_tiptap_editor.widgets.admin_tiptap import AdminTipTapWidget


class TipTapModelAdminMixin:
    """Use ``AdminTipTapWidget`` for the admin's ``TextField`` form fields.

    ``tiptap_fields`` is ``"__all__"`` (every ``TextField``) or an explicit list
    of field names. Mix in before ``admin.ModelAdmin``.
    """

    tiptap_fields: str | list[str] = "__all__"

    def _tiptap_applies(self, db_field: models.Field) -> bool:
        return self.tiptap_fields == "__all__" or db_field.name in self.tiptap_fields

    def formfield_for_dbfield(self, db_field: models.Field, request: Any, **kwargs: Any) -> Any:
        if isinstance(db_field, models.TextField) and self._tiptap_applies(db_field):
            kwargs["widget"] = AdminTipTapWidget
        # super() resolves to admin.ModelAdmin via the consumer's MRO.
        return super().formfield_for_dbfield(  # ty: ignore[unresolved-attribute]
            db_field, request, **kwargs
        )
