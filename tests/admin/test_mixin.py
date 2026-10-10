from __future__ import annotations

import json
from typing import Any

import pytest
from django import forms
from django.contrib import admin
from django.db import models
from django.test import override_settings

from django_tiptap_editor.admin.mixin import TipTapModelAdminMixin
from django_tiptap_editor.constants import STORAGE_FORMAT_JSON
from django_tiptap_editor.forms.fields import TipTapFormField
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
    overrides = {models.TextField: {"max_length": 5, "strip": False, "empty_value": None}}
    form_field = _register(formfield_overrides=overrides).get_form(None).base_fields["body"]
    assert isinstance(form_field, TipTapFormField)
    assert isinstance(form_field.widget, AdminTipTapWidget)
    assert (form_field.max_length, form_field.strip, form_field.empty_value) == (5, False, None)
    assert form_field.clean("<div>short</div>") == "short"


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
