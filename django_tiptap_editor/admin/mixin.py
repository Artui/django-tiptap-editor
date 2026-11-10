from __future__ import annotations

from typing import Any

from django.core import checks
from django.core.exceptions import FieldDoesNotExist
from django.db import models

from django_tiptap_editor.constants import STORAGE_FORMAT_JSON
from django_tiptap_editor.fields.tiptap_json_field import TipTapJSONField
from django_tiptap_editor.forms.fields import TipTapFormField
from django_tiptap_editor.utils.get_storage_format import get_storage_format
from django_tiptap_editor.widgets.admin_tiptap import AdminTipTapWidget
from django_tiptap_editor.widgets.tiptap_widget import TipTapWidget


def _is_editor_field(db_field: Any) -> bool:
    """Whether the mixin would swap the TipTap widget onto this field."""
    return isinstance(db_field, (TipTapJSONField, models.TextField))


def _flatten(fields: Any) -> set[str]:
    """The names in an admin ``fields`` value, where a tuple is one row of several."""
    names: set[str] = set()
    for item in fields:
        names.update(item if isinstance(item, (list, tuple)) else (item,))
    return names


class TipTapModelAdminMixin:
    """Use ``AdminTipTapWidget`` for the admin's TipTap-backed form fields."""

    # Provided by admin.ModelAdmin / InlineModelAdmin via the consumer's MRO.
    model: Any
    form: Any
    fields: Any
    fieldsets: Any
    exclude: Any
    readonly_fields: Any

    tiptap_fields: str | list[str] = "__all__"

    def check(self, **kwargs: Any) -> list[checks.CheckMessage]:
        return [
            *super().check(**kwargs),  # ty: ignore[unresolved-attribute]
            *self._check_tiptap_fields(),
            *self._check_json_storage(),
        ]

    def _check_tiptap_fields(self) -> list[checks.CheckMessage]:
        """Report an explicit ``tiptap_fields`` entry the mixin would ignore."""
        if isinstance(self.tiptap_fields, str):
            if self.tiptap_fields == "__all__":
                return []
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

    def _override_for(self, db_field: models.Field) -> tuple[type, dict[str, Any]]:
        """The ``formfield_overrides`` entry Django will apply to this field."""
        overrides = getattr(self, "formfield_overrides", {})
        for klass in type(db_field).mro():
            if klass in overrides:
                return klass, overrides[klass]
        return object, {}

    def _overrides_form_class(self, db_field: models.Field) -> bool:
        """Whether ``formfield_overrides`` gives this field its own form class."""
        return "form_class" in self._override_for(db_field)[1]

    def _overriding_widget(self, db_field: models.Field) -> TipTapWidget | None:
        """The TipTap widget ``formfield_overrides`` gives this field, if any."""
        widget = self._override_for(db_field)[1].get("widget")
        if isinstance(widget, type) and issubclass(widget, TipTapWidget):
            return widget()
        return widget if isinstance(widget, TipTapWidget) else None

    def _override_widget_renders(self, name: str) -> bool:
        """Whether a ``formfield_overrides`` widget can reach this field's form."""
        widgets = getattr(getattr(self.form, "_meta", None), "widgets", None)
        if name in (widgets or {}):
            return False
        if name in self.form.declared_fields:
            return False
        if name in (self.readonly_fields or ()) or name in (self.exclude or ()):
            return False
        if self.fields is not None and name not in _flatten(self.fields):
            return False
        return self.fieldsets is None or name in _flatten(
            field for _, options in self.fieldsets for field in options["fields"]
        )

    def _check_json_storage(self) -> list[checks.CheckMessage]:
        """Warn of a project TipTap widget on a JSON field that writes HTML."""
        warnings: list[checks.CheckMessage] = []
        for db_field in self.model._meta.get_fields():
            if not isinstance(db_field, TipTapJSONField) or not self._tiptap_applies(db_field):
                continue
            try:
                widget = self._overriding_widget(db_field)
            except TypeError:
                continue
            if widget is None or (widget.storage or get_storage_format()) == STORAGE_FORMAT_JSON:
                continue
            try:
                renders = self._override_widget_renders(db_field.name)
            except (AttributeError, KeyError, TypeError, ValueError):
                continue
            if renders:
                warnings.append(
                    checks.Warning(
                        f"The widget formfield_overrides gives '{db_field.name}', a "
                        f"TipTapJSONField, is a {type(widget).__name__} in HTML storage, "
                        "so the editor would write HTML into a JSON field and every save "
                        'would fail. Pass storage="json" to the widget. This may not '
                        "apply if get_form, get_fields, get_exclude, get_readonly_fields "
                        "or get_fieldsets keeps the widget off the field.",
                        obj=type(self),
                        id="django_tiptap_editor.W001",
                    )
                )
        return warnings

    def formfield_for_dbfield(self, db_field: models.Field, request: Any, **kwargs: Any) -> Any:
        if self._tiptap_applies(db_field):
            # A TipTap widget the project chose is the one rendered, config and all: one from ``formfield_overrides`` (see ``_overriding_widget``) or any widget from its form's ``Meta.widgets``, which names one field and reaches this method as ``kwargs["widget"]``, hence ``setdefault``.
            own_widget = self._overriding_widget(db_field) is not None
            if isinstance(db_field, TipTapJSONField):
                if not own_widget:
                    kwargs.setdefault("widget", AdminTipTapWidget(storage=STORAGE_FORMAT_JSON))
            elif isinstance(db_field, models.TextField):
                if not own_widget:
                    kwargs.setdefault("widget", AdminTipTapWidget)
                if not self._overrides_form_class(db_field):
                    kwargs.setdefault("form_class", TipTapFormField)
        return super().formfield_for_dbfield(  # ty: ignore[unresolved-attribute]
            db_field, request, **kwargs
        )
