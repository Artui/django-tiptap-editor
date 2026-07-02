"""ModelAdmin mixin that swaps the admin TipTap widget onto editor fields."""

from __future__ import annotations

from typing import Any

from django.db import models

from django_tiptap_editor.constants import STORAGE_FORMAT_JSON
from django_tiptap_editor.fields.tiptap_json_field import TipTapJSONField
from django_tiptap_editor.widgets.admin_tiptap import AdminTipTapWidget


class TipTapModelAdminMixin:
    """Use ``AdminTipTapWidget`` for the admin's TipTap-backed form fields.

    Covers plain ``TextField``s (HTML storage) *and* ``TipTapJSONField``s (JSON
    storage) — the JSON field gets the admin widget in JSON storage mode so its
    ``{doc, html}`` envelope still round-trips. ``tiptap_fields`` is ``"__all__"``
    (every eligible field) or an explicit list of field names. Mix in before
    ``admin.ModelAdmin``.
    """

    tiptap_fields: str | list[str] = "__all__"

    def _tiptap_applies(self, db_field: models.Field) -> bool:
        return self.tiptap_fields == "__all__" or db_field.name in self.tiptap_fields

    def formfield_for_dbfield(self, db_field: models.Field, request: Any, **kwargs: Any) -> Any:
        if self._tiptap_applies(db_field):
            if isinstance(db_field, TipTapJSONField):
                # An instance (not the class) so JSON storage is pinned — the
                # class would resolve storage from settings and could serialize
                # HTML into a JSON column.
                kwargs["widget"] = AdminTipTapWidget(storage=STORAGE_FORMAT_JSON)
            elif isinstance(db_field, models.TextField):
                kwargs["widget"] = AdminTipTapWidget
        # super() resolves to admin.ModelAdmin via the consumer's MRO.
        return super().formfield_for_dbfield(  # ty: ignore[unresolved-attribute]
            db_field, request, **kwargs
        )
