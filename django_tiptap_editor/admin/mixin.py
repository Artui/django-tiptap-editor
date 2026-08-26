"""ModelAdmin mixin that swaps the admin TipTap widget onto editor fields."""

from __future__ import annotations

from typing import Any

from django.core import checks
from django.core.exceptions import FieldDoesNotExist
from django.db import models

from django_tiptap_editor.constants import STORAGE_FORMAT_JSON
from django_tiptap_editor.fields.tiptap_json_field import TipTapJSONField
from django_tiptap_editor.widgets.admin_tiptap import AdminTipTapWidget


def _is_editor_field(db_field: Any) -> bool:
    """Whether the mixin would swap the TipTap widget onto this field."""
    # TipTapJSONField is a JSONField, not a TextField, so both are named.
    return isinstance(db_field, (TipTapJSONField, models.TextField))


class TipTapModelAdminMixin:
    """Use ``AdminTipTapWidget`` for the admin's TipTap-backed form fields.

    Covers plain ``TextField``s (HTML storage) *and* ``TipTapJSONField``s (JSON
    storage) — the JSON field gets the admin widget in JSON storage mode so its
    ``{doc, html}`` envelope still round-trips. ``tiptap_fields`` is ``"__all__"``
    (every eligible field) or an explicit list of field names. Mix in before
    ``admin.ModelAdmin``.

    ``tiptap_fields`` is checked at startup by Django's check framework
    (``django_tiptap_editor.E001`` to ``E003``): a name that is not a field on
    the model, or one naming a field the widget cannot apply to, used to be a
    silent no-op — the admin simply rendered a plain textarea and nothing said
    why.
    """

    # Provided by admin.ModelAdmin / InlineModelAdmin via the consumer's MRO.
    model: Any

    tiptap_fields: str | list[str] = "__all__"

    def check(self, **kwargs: Any) -> list[checks.CheckMessage]:
        return [
            *super().check(**kwargs),  # ty: ignore[unresolved-attribute]
            *self._check_tiptap_fields(),
        ]

    def _check_tiptap_fields(self) -> list[checks.CheckMessage]:
        """Report an explicit ``tiptap_fields`` entry the mixin would ignore."""
        if isinstance(self.tiptap_fields, str):
            if self.tiptap_fields == "__all__":
                return []
            # A bare string is worse than ignored: `db_field.name in "somebody"`
            # is a substring test, so it matches fields nobody named.
            return [
                checks.Error(
                    "'tiptap_fields' must be '__all__' or a list of field names, "
                    f"not the string {self.tiptap_fields!r}.",
                    obj=type(self),
                    id="django_tiptap_editor.E001",
                )
            ]
        errors: list[checks.CheckMessage] = []
        for name in self.tiptap_fields:
            try:
                db_field = self.model._meta.get_field(name)
            except FieldDoesNotExist:
                errors.append(
                    checks.Error(
                        f"'tiptap_fields' names '{name}', which is not a field on "
                        f"{self.model._meta.label}.",
                        obj=type(self),
                        id="django_tiptap_editor.E002",
                    )
                )
                continue
            if not _is_editor_field(db_field):
                errors.append(
                    checks.Error(
                        f"'tiptap_fields' names '{name}', which is a "
                        f"{type(db_field).__name__}. The TipTap widget applies only to "
                        "TextField and TipTapJSONField.",
                        obj=type(self),
                        id="django_tiptap_editor.E003",
                    )
                )
        return errors

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
