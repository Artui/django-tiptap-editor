from __future__ import annotations

import json
from typing import Any

import pytest
from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import AdminTextareaWidget
from django.core import checks
from django.core.exceptions import ValidationError
from django.db import models
from django.test import override_settings

from django_tiptap_editor.admin.mixin import TipTapModelAdminMixin
from django_tiptap_editor.constants import STORAGE_FORMAT_JSON
from django_tiptap_editor.fields.tiptap_json_field import TipTapJSONField
from django_tiptap_editor.forms.fields import TipTapFormField
from django_tiptap_editor.widgets.admin_tiptap import AdminTipTapWidget
from django_tiptap_editor.widgets.tiptap_widget import TipTapWidget
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


DOC = {
    "type": "doc",
    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "hi"}]}],
}


def _register(**attrs: Any) -> admin.ModelAdmin:
    """Register an Article admin built from the mixin on a throwaway AdminSite."""
    site = admin.AdminSite()
    site.register(Article, type("ArticleAdmin", (TipTapModelAdminMixin, admin.ModelAdmin), attrs))
    return site._registry[Article]


def _check_ids(**attrs: Any) -> list[str]:
    return [error.id for error in _register(**attrs).check()]


@pytest.mark.django_db
def test_admin_form_round_trips_a_json_document() -> None:
    # The mixin's own admin form — the package's most common deployment.
    model_admin = _register()
    form = model_admin.get_form(None)(
        data={
            "title": "t",
            "body": "b",
            "summary": "",
            "document": json.dumps({"doc": DOC, "html": "<p>hi</p>"}),
        }
    )
    assert form.is_valid(), form.errors
    article = form.save()
    assert Article.objects.get(pk=article.pk).document.doc == DOC


HOSTILE = '<p>x</p><script>alert(1)</script><img src="javascript:alert(1)" onerror="x()">'


def _admin_form(model_admin: admin.ModelAdmin, **data: str) -> forms.ModelForm:
    return model_admin.get_form(None)(data={"title": "t", "body": "b", "summary": "", **data})


def test_an_admin_textfield_is_sanitised_on_save() -> None:
    # The widget alone was swapped, so the form field stayed a plain CharField
    # and the admin stored a direct POST exactly as sent.
    form = _admin_form(_register(), body=HOSTILE)
    assert form.is_valid(), form.errors
    assert form.cleaned_data["body"] == "<p>x</p><img>"


def test_the_admin_textfield_keeps_the_options_a_project_sets() -> None:
    # TipTapFormField is a CharField, so the options a project already passes to
    # an admin text field reach it unchanged, and still count the stored value.
    # Each option is checked by cleaning a value through it, not by reading the
    # attribute back: the sanitiser runs after CharField's own conversion, and
    # an option it undid would still read back as set.
    overrides = {models.TextField: {"max_length": 5, "strip": False, "empty_value": None}}
    fields = _register(formfield_overrides=overrides).get_form(None).base_fields
    form_field = fields["body"]
    assert isinstance(form_field, TipTapFormField)
    assert isinstance(form_field.widget, AdminTipTapWidget)
    # max_length counts what is stored, so markup the sanitiser removes is free.
    assert form_field.clean("<div>short</div>") == "short"
    with pytest.raises(ValidationError):
        form_field.clean("<div>toolong</div>")
    # strip=False keeps the whitespace a stripping CharField would remove.
    assert form_field.clean(" ab ") == " ab "
    # empty_value=None is what a nullable column relies on to store NULL; the
    # summary column is optional, so an empty submission reaches it.
    optional = fields["summary"]
    assert isinstance(optional, TipTapFormField)
    assert optional.clean("") is None
    assert optional.clean(None) is None


def test_a_projects_own_form_class_wins() -> None:
    class Plain(forms.CharField):
        """A project's own field class for its text columns."""

    overrides = {models.TextField: {"form_class": Plain}}
    assert type(_register(formfield_overrides=overrides).get_form(None).base_fields["body"]) is (
        Plain
    )

    class ArticleForm(forms.ModelForm):
        class Meta:
            model = Article
            fields = "__all__"
            field_classes = {"body": Plain}

    form_fields = _register(form=ArticleForm).get_form(None).base_fields
    assert type(form_fields["body"]) is Plain
    assert isinstance(form_fields["summary"], TipTapFormField)


def test_a_form_class_django_would_not_apply_does_not_stop_the_editors() -> None:
    # Django applies the overrides of the first class in a field's MRO that has
    # an entry, and TextField always has one (the admin's own textarea), so a
    # form class given for Field never reaches a TextField and must not stop
    # this mixin's from reaching it either.
    overrides = {models.Field: {"form_class": forms.CharField}}
    form_field = _register(formfield_overrides=overrides).get_form(None).base_fields["body"]
    assert isinstance(form_field, TipTapFormField)


@override_settings(TIPTAP_DEFAULT_CONFIG={"features": ["bold"]})
def test_a_project_wide_feature_list_narrows_the_admin() -> None:
    form = _admin_form(_register(), body="<h2>a</h2><ul><li><p>b</p></li></ul>")
    assert form.is_valid(), form.errors
    assert form.cleaned_data["body"] == "<p>a</p><p>b</p>"


def test_a_declared_admin_field_narrows_to_its_own_features() -> None:
    # The per-field route the mixin leaves open: a field declared on the admin's
    # form is not built by formfield_for_dbfield, so its widget is the one given.
    class ArticleForm(forms.ModelForm):
        body = TipTapFormField(widget=AdminTipTapWidget(config={"features": ["bold"]}))

        class Meta:
            model = Article
            fields = "__all__"

    form = _admin_form(_register(form=ArticleForm), body="<h2>a</h2><p><strong>b</strong></p>")
    assert form.is_valid(), form.errors
    assert form.cleaned_data["body"] == "<p>a</p><p><strong>b</strong></p>"


@pytest.mark.django_db
@override_settings(TIPTAP_DEFAULT_CONFIG={"features": ["bold"]})
def test_an_admin_json_field_narrows_its_document() -> None:
    text = [{"type": "text", "text": "hi"}]
    heading = {
        "type": "doc",
        "content": [{"type": "heading", "attrs": {"level": 2}, "content": text}],
    }
    form = _admin_form(_register(), document=json.dumps({"doc": heading, "html": ""}))
    assert form.is_valid(), form.errors
    article = form.save()
    stored = Article.objects.get(pk=article.pk).document
    assert stored.doc == DOC
    assert stored.html == "<p>hi</p>"


def test_check_passes_for_the_default_and_for_valid_names() -> None:
    assert _check_ids() == []
    assert _check_ids(tiptap_fields=["body", "document"]) == []


def test_check_flags_a_name_that_is_not_a_field() -> None:
    # Previously a silent no-op: the admin rendered a plain textarea, no warning.
    model_admin = _register(tiptap_fields=["published_at"])
    errors = [e for e in model_admin.check() if e.id == "django_tiptap_editor.E002"]
    assert len(errors) == 1
    assert "published_at" in errors[0].msg


def test_check_flags_an_ineligible_field_type() -> None:
    model_admin = _register(tiptap_fields=["title"])
    errors = [e for e in model_admin.check() if e.id == "django_tiptap_editor.E003"]
    assert len(errors) == 1
    assert "CharField" in errors[0].msg


def test_check_flags_a_bare_string() -> None:
    # `db_field.name in "somebody"` is a substring test, so this silently matched
    # fields nobody named.
    assert _check_ids(tiptap_fields="somebody") == ["django_tiptap_editor.E001"]


def test_check_runs_from_the_admin_site() -> None:
    # The real startup path: registered admins are checked by the site.
    site = admin.AdminSite()
    site.register(
        Article,
        type("BadAdmin", (TipTapModelAdminMixin, admin.ModelAdmin), {"tiptap_fields": ["nope"]}),
    )
    assert [e.id for e in site.check(None)] == ["django_tiptap_editor.E002"]


# A project's own TipTap widget, given through ``formfield_overrides`` or a form's
# ``Meta.widgets``, is the one the admin renders: the mixin used to replace it with
# a bare ``AdminTipTapWidget``, so a ``height`` (or any config) set there never
# arrived. A ``formfield_overrides`` entry is class-wide, though, so a widget there
# that is not a TipTap widget (a smaller textarea for every TextField, say) is
# about the fields the mixin does not apply to, and the editor still replaces it.


class _TallerWidget(AdminTipTapWidget):
    """A project's own subclass, given as a class rather than an instance."""

    admin_defaults = {"height": "700px"}


def test_a_projects_own_textfield_widget_wins() -> None:
    overrides = {models.TextField: {"widget": AdminTipTapWidget(config={"height": "200px"})}}
    form_field = _register(formfield_overrides=overrides).get_form(None).base_fields["body"]
    assert isinstance(form_field.widget, AdminTipTapWidget)
    assert form_field.widget.get_config({})["height"] == "200px"
    # Only the widget was the project's, so the field still sanitises.
    assert isinstance(form_field, TipTapFormField)


def test_a_tiptap_widget_subclass_given_as_a_class_wins() -> None:
    overrides = {models.TextField: {"widget": _TallerWidget}}
    form_field = _register(formfield_overrides=overrides).get_form(None).base_fields["body"]
    assert type(form_field.widget) is _TallerWidget
    assert form_field.widget.get_config({})["height"] == "700px"


def test_a_plain_tiptap_widget_instance_wins() -> None:
    overrides = {models.TextField: {"widget": TipTapWidget(config={"height": "200px"})}}
    form_field = _register(formfield_overrides=overrides).get_form(None).base_fields["body"]
    assert type(form_field.widget) is TipTapWidget
    assert form_field.widget.get_config({})["height"] == "200px"


@pytest.mark.parametrize("tiptap_fields", ["__all__", ["body", "document"]])
@pytest.mark.parametrize("widget", [forms.Textarea, forms.Textarea(attrs={"rows": 3})])
def test_a_class_wide_widget_that_is_not_tiptap_does_not_replace_the_editor(
    tiptap_fields: str | list[str], widget: object
) -> None:
    overrides = {
        models.TextField: {"widget": widget},
        TipTapJSONField: {"widget": widget},
    }
    fields = (
        _register(formfield_overrides=overrides, tiptap_fields=tiptap_fields)
        .get_form(None)
        .base_fields
    )
    assert type(fields["body"].widget) is AdminTipTapWidget
    assert isinstance(fields["body"], TipTapFormField)
    assert type(fields["document"].widget) is AdminTipTapWidget
    assert fields["document"].widget.storage == STORAGE_FORMAT_JSON
    # A field the mixin does not apply to gets the project's widget as Django
    # would give it.
    if tiptap_fields != "__all__":
        assert type(fields["summary"].widget) is forms.Textarea


def test_the_admins_own_textarea_default_does_not_stop_the_editor() -> None:
    # ModelAdmin merges its defaults into formfield_overrides, so TextField always
    # has an entry naming AdminTextareaWidget. That entry is Django's, not the
    # project's: read as an override, it would take the editor off every admin.
    model_admin = _register()
    assert model_admin.formfield_overrides[models.TextField]["widget"] is AdminTextareaWidget
    assert isinstance(model_admin.get_form(None).base_fields["body"].widget, AdminTipTapWidget)


def test_a_projects_own_json_field_widget_wins() -> None:
    widget = AdminTipTapWidget(storage=STORAGE_FORMAT_JSON, config={"height": "200px"})
    overrides = {TipTapJSONField: {"widget": widget}}
    form_field = _register(formfield_overrides=overrides).get_form(None).base_fields["document"]
    assert form_field.widget.get_config({})["height"] == "200px"
    assert form_field.widget.storage == STORAGE_FORMAT_JSON


def test_a_json_field_widget_without_json_storage_fails_loudly() -> None:
    # The mixin uses the project's widget as given, so one left in HTML storage
    # makes the glue write HTML into a JSON field. docs/api.md says that fails
    # validation on save rather than storing something else; this holds it.
    overrides = {TipTapJSONField: {"widget": AdminTipTapWidget(config={"height": "200px"})}}
    model_admin = _register(formfield_overrides=overrides)
    rendered = model_admin.get_form(None)()["document"].as_widget()
    assert 'data-tiptap-storage="html"' in rendered
    form = _admin_form(model_admin, document="<p>hi</p>")
    assert not form.is_valid()
    assert "document" in form.errors


def test_a_widget_override_follows_djangos_mro_lookup() -> None:
    # Django applies the entry of the first class in the field's MRO that has
    # one. TextField's first entry is the admin's own, so an entry for Field
    # never reaches it; a TipTapJSONField has no entry of its own, so it does.
    widget = AdminTipTapWidget(storage=STORAGE_FORMAT_JSON, config={"height": "200px"})
    fields = (
        _register(formfield_overrides={models.Field: {"widget": widget}}).get_form(None).base_fields
    )
    assert fields["body"].widget.get_config({})["height"] == "500px"
    assert fields["document"].widget.get_config({})["height"] == "200px"


def test_a_widget_from_the_forms_meta_wins() -> None:
    # Meta.widgets names one field, so any widget there is the project's choice
    # for it, TipTap or not. It reaches the mixin as kwargs["widget"]; assigning
    # the admin widget over it, rather than setdefault, would lose all three.
    class ArticleForm(forms.ModelForm):
        class Meta:
            model = Article
            fields = "__all__"
            widgets = {
                "body": AdminTipTapWidget(config={"height": "200px"}),
                "summary": forms.Textarea(attrs={"rows": 3}),
                "document": AdminTipTapWidget(
                    storage=STORAGE_FORMAT_JSON, config={"height": "250px"}
                ),
            }

    fields = _register(form=ArticleForm).get_form(None).base_fields
    assert fields["body"].widget.get_config({})["height"] == "200px"
    assert isinstance(fields["body"], TipTapFormField)
    assert type(fields["summary"].widget) is forms.Textarea
    assert isinstance(fields["summary"], TipTapFormField)
    assert fields["document"].widget.get_config({})["height"] == "250px"


# A project's TipTap widget on a JSON field that is not in JSON storage writes
# HTML into it, and every save fails. Before the mixin honoured the widget it was
# silently replaced, so the configuration only started failing when it started
# being used: E004 says so at startup instead.


def _e004(**attrs: Any) -> list[checks.CheckMessage]:
    return [e for e in _register(**attrs).check() if e.id == "django_tiptap_editor.E004"]


@pytest.mark.parametrize(
    "widget", [AdminTipTapWidget, AdminTipTapWidget(config={"height": "200px"}), TipTapWidget()]
)
def test_check_flags_a_json_field_widget_not_in_json_storage(widget: object) -> None:
    model_admin = _register(formfield_overrides={TipTapJSONField: {"widget": widget}})
    errors = [e for e in model_admin.check() if e.id == "django_tiptap_editor.E004"]
    assert len(errors) == 1
    assert errors[0].obj is type(model_admin)
    assert "'document'" in errors[0].msg
    assert 'storage="json"' in errors[0].msg


def test_check_passes_a_json_field_widget_in_json_storage() -> None:
    widget = AdminTipTapWidget(storage=STORAGE_FORMAT_JSON)
    assert _e004(formfield_overrides={TipTapJSONField: {"widget": widget}}) == []


@override_settings(TIPTAP_STORAGE_FORMAT="json")
def test_check_passes_a_widget_that_takes_json_storage_from_settings() -> None:
    # Unpinned, but the project-wide format is JSON, so it writes the envelope.
    assert _e004(formfield_overrides={TipTapJSONField: {"widget": AdminTipTapWidget}}) == []


def test_check_passes_an_html_widget_on_a_text_field() -> None:
    # HTML storage is right for a TextField, which is what a TipTap widget on
    # one usually is: only the JSON field is held to the envelope.
    assert _e004(formfield_overrides={models.TextField: {"widget": _TallerWidget}}) == []


def test_check_ignores_widgets_the_mixin_does_not_use() -> None:
    # A non-TipTap widget is replaced by the mixin's own, and a field the mixin
    # does not apply to is Django's business, not this check's.
    assert _e004(formfield_overrides={TipTapJSONField: {"widget": forms.Textarea}}) == []
    assert (
        _e004(
            formfield_overrides={TipTapJSONField: {"widget": AdminTipTapWidget}},
            tiptap_fields=["body"],
        )
        == []
    )
