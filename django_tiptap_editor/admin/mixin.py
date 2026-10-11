"""ModelAdmin mixin that swaps the admin TipTap widget onto editor fields."""

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
    # TipTapJSONField is a JSONField, not a TextField, so both are named.
    return isinstance(db_field, (TipTapJSONField, models.TextField))


class TipTapModelAdminMixin:
    """Use ``AdminTipTapWidget`` for the admin's TipTap-backed form fields.

    Covers plain ``TextField``s (HTML storage) *and* ``TipTapJSONField``s (JSON
    storage) — the JSON field gets the admin widget in JSON storage mode so its
    ``{doc, html}`` envelope still round-trips. A ``TextField`` also gets
    ``TipTapFormField`` as its form class, so what the admin saves is sanitised
    (unless the project gives that field a form class of its own, through
    ``formfield_overrides`` or ``Meta.field_classes``). The admin widget is a
    default too, and a widget the project chose is rendered as given, so its
    ``config`` (``height`` and the rest) applies: a TipTap widget (a
    ``TipTapWidget`` subclass or instance) from ``formfield_overrides``, or any
    widget from the form's ``Meta.widgets``. A ``formfield_overrides`` widget that
    is not a TipTap widget is class-wide, so it is taken to be for the fields the
    mixin leaves alone, and the editor still replaces it on the ones it applies
    to. ``tiptap_fields`` is ``"__all__"`` (every eligible field) or an explicit
    list of field names. Mix in before ``admin.ModelAdmin``.

    ``tiptap_fields`` is checked at startup by Django's check framework
    (``django_tiptap_editor.E001`` to ``E003``): a name that is not a field on
    the model, or one naming a field the widget cannot apply to, used to be a
    silent no-op — the admin simply rendered a plain textarea and nothing said
    why. ``E004`` flags a TipTap widget from ``formfield_overrides`` on a
    ``TipTapJSONField`` that would render in HTML storage, so every save would
    fail.
    """

    # Provided by admin.ModelAdmin / InlineModelAdmin via the consumer's MRO.
    model: Any

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

    def _override_for(self, db_field: models.Field) -> tuple[type, dict[str, Any]]:
        """The ``formfield_overrides`` entry Django will apply to this field.

        Django applies the entry of the first class in the field's MRO that has
        one, and merges the kwargs passed here *over* it, so anything set here
        would beat the project's. Looked up the same way, so the project's wins.
        Returns the class the entry belongs to as well, so a caller can tell the
        admin's own defaults from the project's. ``(object, {})`` when no class
        has an entry.
        """
        overrides = getattr(self, "formfield_overrides", {})
        for klass in type(db_field).mro():
            if klass in overrides:
                return klass, overrides[klass]
        return object, {}

    def _overrides_form_class(self, db_field: models.Field) -> bool:
        """Whether ``formfield_overrides`` gives this field its own form class."""
        return "form_class" in self._override_for(db_field)[1]

    def _overriding_widget(self, db_field: models.Field) -> TipTapWidget | None:
        """The TipTap widget ``formfield_overrides`` gives this field, if any.

        An entry there is class-wide, so only a TipTap widget (a subclass, or an
        instance of one) is read as meant for the editor. Anything else, such as
        a smaller textarea for every ``TextField``, is about the fields the mixin
        does not touch, and is replaced on the ones it does, as it always was.
        That also covers the ``AdminTextareaWidget`` entry ``ModelAdmin.__init__``
        merges in for every ``TextField``. A class is returned instantiated, which
        is what Django would do with it.
        """
        widget = self._override_for(db_field)[1].get("widget")
        if isinstance(widget, type) and issubclass(widget, TipTapWidget):
            return widget()
        return widget if isinstance(widget, TipTapWidget) else None

    def _check_json_storage(self) -> list[checks.CheckMessage]:
        """Report a project TipTap widget on a JSON field that writes HTML.

        The mixin renders such a widget as given, and the glue then writes HTML
        into a field that parses a JSON envelope, so every save fails. The
        storage checked is the one the widget will render with: its own, or
        ``TIPTAP_STORAGE_FORMAT`` when it names none.
        """
        errors: list[checks.CheckMessage] = []
        for db_field in self.model._meta.get_fields():
            # The type check is held by ``test_check_passes_an_html_widget_on_a_text_field``
            # (HTML is right for a TextField), the scope check by
            # ``test_check_ignores_widgets_the_mixin_does_not_use``.
            if not isinstance(db_field, TipTapJSONField) or not self._tiptap_applies(db_field):
                continue
            widget = self._overriding_widget(db_field)
            # Without the None check a field with no TipTap widget raises
            # AttributeError (``test_check_ignores_widgets_the_mixin_does_not_use``);
            # without the storage check every TipTap widget is flagged
            # (``test_check_passes_a_json_field_widget_in_json_storage``).
            if widget is not None and (widget.storage or get_storage_format()) != (
                STORAGE_FORMAT_JSON
            ):
                errors.append(
                    checks.Error(
                        f"The widget formfield_overrides gives '{db_field.name}', a "
                        f"TipTapJSONField, is a {type(widget).__name__} in HTML storage, "
                        "so the editor would write HTML into a JSON field and every save "
                        'would fail. Pass storage="json" to the widget.',
                        obj=type(self),
                        id="django_tiptap_editor.E004",
                    )
                )
        return errors

    def formfield_for_dbfield(self, db_field: models.Field, request: Any, **kwargs: Any) -> Any:
        if self._tiptap_applies(db_field):
            # A TipTap widget the project chose is the one rendered, config and
            # all: one from ``formfield_overrides`` (see ``_overriding_widget``)
            # or any widget from its form's ``Meta.widgets``, which names one
            # field and reaches this method as ``kwargs["widget"]``, hence
            # ``setdefault``. Replacing them is how a ``height`` set there used
            # to vanish. The admin widget is only the default.
            own_widget = self._overriding_widget(db_field) is not None
            if isinstance(db_field, TipTapJSONField):
                if not own_widget:
                    # An instance (not the class) so JSON storage is pinned — the
                    # class would resolve storage from settings and could
                    # serialize HTML into a JSON column.
                    kwargs.setdefault("widget", AdminTipTapWidget(storage=STORAGE_FORMAT_JSON))
            elif isinstance(db_field, models.TextField):
                if not own_widget:
                    kwargs.setdefault("widget", AdminTipTapWidget)
                # The widget alone left the form field a plain CharField, so the
                # admin stored a direct POST unsanitised. Applied whichever widget
                # renders: a project's own widget is no reason to store its POST
                # raw. ``setdefault`` keeps a ``form_class`` already passed in
                # (``Meta.field_classes``).
                if not self._overrides_form_class(db_field):
                    kwargs.setdefault("form_class", TipTapFormField)
        # super() resolves to admin.ModelAdmin via the consumer's MRO.
        return super().formfield_for_dbfield(  # ty: ignore[unresolved-attribute]
            db_field, request, **kwargs
        )
