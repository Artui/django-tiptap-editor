from __future__ import annotations

import json

import pytest
from django.core.exceptions import ValidationError
from django.forms import modelform_factory
from django.test import override_settings

from django_tiptap_editor.fields.tiptap_json_field import (
    _RENDERABLE_MARK_TYPES,
    _RENDERABLE_NODE_TYPES,
    TipTapJSONField,
    _unknown_types,
)
from django_tiptap_editor.forms.json_field import TipTapJSONFormField
from django_tiptap_editor.types.tiptap_value import TipTapValue
from django_tiptap_editor.utils.render_doc import render_doc
from tests.testapp.models import Article

DOC = {
    "type": "doc",
    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "hi"}]}],
}


def test_to_python_passthrough_and_none() -> None:
    field = TipTapJSONField()
    value = TipTapValue.from_stored({"doc": DOC, "html": "<p>hi</p>"})
    assert field.to_python(value) is value
    assert field.to_python(None) is None


def test_to_python_parses_a_mapping() -> None:
    from_dict = TipTapJSONField().to_python({"doc": {"type": "doc"}, "html": "<p></p>"})
    assert from_dict.doc == {"type": "doc"}


def test_to_python_parses_a_json_string() -> None:
    """A JSON string is legitimate input -- a fixture, a deserializer -- and is parsed.

    ``models.JSONField`` defines no ``to_python``, so this field's ``super()`` call
    was ``Field.to_python``, a no-op: the string arrived at ``from_stored`` unparsed
    and silently became an empty document.
    """
    value = TipTapJSONField().to_python(json.dumps({"doc": DOC, "html": "<p>hi</p>"}))
    assert value.doc == DOC


def test_to_python_refuses_a_string_that_is_not_json() -> None:
    with pytest.raises(ValidationError):
        TipTapJSONField().to_python("not json at all")


def test_to_python_refuses_json_that_is_not_a_document() -> None:
    with pytest.raises(ValidationError):
        TipTapJSONField().to_python("[1, 2, 3]")


def test_a_legacy_mirror_survives_a_save_when_the_doc_is_empty() -> None:
    """The documented HTML-to-JSON migration seeds rows as ``{"doc": {}, "html": ...}``.

    Deriving the mirror from an empty doc renders "" and destroys the content on the
    next save, so the seeded mirror is kept -- already sanitised, because
    ``TipTapValue`` runs it through the allowlist on construction.
    """
    stored = TipTapJSONField().get_prep_value({"doc": {}, "html": "<p>legacy</p>"})
    assert stored["html"] == "<p>legacy</p>"


def test_a_kept_legacy_mirror_is_still_sanitized() -> None:
    stored = TipTapJSONField().get_prep_value({"doc": {}, "html": "<img src=x onerror=alert(1)>"})
    assert "onerror" not in stored["html"]


def test_get_prep_value_none() -> None:
    assert TipTapJSONField().get_prep_value(None) is None


def test_get_prep_value_sanitizes_doc() -> None:
    field = TipTapJSONField()
    evil = {
        "type": "doc",
        "content": [
            {
                "type": "text",
                "text": "x",
                "marks": [{"type": "link", "attrs": {"href": "javascript:alert(1)"}}],
            }
        ],
    }
    prepared = field.get_prep_value(TipTapValue.from_stored({"doc": evil, "html": "<p>x</p>"}))
    # get_prep_value returns the {doc, html} mapping; the disallowed mark is gone.
    assert prepared["doc"]["content"][0]["marks"] == []


def test_formfield_uses_json_form_field() -> None:
    field = TipTapJSONField()
    form_field = field.formfield()
    assert isinstance(form_field, TipTapJSONFormField)
    assert form_field.widget.storage == "json"


@pytest.mark.django_db
def test_db_roundtrip_returns_tiptap_value() -> None:
    article = Article.objects.create(
        title="t",
        body="",
        document=TipTapValue.from_stored({"doc": DOC, "html": "<p>hi</p>"}),
    )
    reloaded = Article.objects.get(pk=article.pk)
    assert isinstance(reloaded.document, TipTapValue)
    assert reloaded.document.doc == DOC
    assert reloaded.document.html == "<p>hi</p>"


@pytest.mark.django_db
def test_db_roundtrip_null() -> None:
    article = Article.objects.create(title="t", body="", document=None)
    assert Article.objects.get(pk=article.pk).document is None


def test_get_prep_value_derives_mirror_when_html_missing() -> None:
    # Programmatic write: doc set, no html → mirror rendered server-side.
    prepared = TipTapJSONField().get_prep_value(TipTapValue.from_stored({"doc": DOC}))
    assert prepared["html"] == "<p>hi</p>"


def test_get_prep_value_rederives_mirror_ignoring_caller_html() -> None:
    # A caller-supplied html mirror is discarded and re-derived from the doc.
    prepared = TipTapJSONField().get_prep_value(
        TipTapValue.from_stored({"doc": DOC, "html": "<p>custom</p>"})
    )
    assert prepared["html"] == "<p>hi</p>"


def test_get_prep_value_discards_hostile_caller_html() -> None:
    # Benign doc, hostile html mirror (an API / import / hand-edit write). The
    # stored mirror must reflect only the sanitized doc, never the caller markup.
    prepared = TipTapJSONField().get_prep_value(
        TipTapValue.from_stored({"doc": DOC, "html": '<img src=x onerror="alert(1)">'})
    )
    assert prepared["html"] == "<p>hi</p>"
    assert "onerror" not in prepared["html"]


def test_get_prep_value_empty_doc_keeps_empty_html() -> None:
    prepared = TipTapJSONField().get_prep_value(TipTapValue.from_stored({"doc": {}, "html": ""}))
    assert prepared["html"] == ""


@pytest.mark.django_db
def test_db_save_strips_disallowed_link() -> None:
    evil = {
        "type": "doc",
        "content": [
            {
                "type": "text",
                "text": "x",
                "marks": [{"type": "link", "attrs": {"href": "javascript:alert(1)"}}],
            }
        ],
    }
    article = Article.objects.create(
        title="t", body="", document=TipTapValue.from_stored({"doc": evil, "html": "<p>x</p>"})
    )
    doc = Article.objects.get(pk=article.pk).document.doc
    assert doc["content"][0]["marks"] == []


STORED = json.dumps({"doc": DOC, "html": "<p>hi</p>"})
ArticleForm = modelform_factory(Article, fields=["title", "body", "document"])


def _unknown_node_doc(kind: str) -> dict[str, object]:
    return {
        "type": "doc",
        "content": [{"type": kind, "content": [{"type": "text", "text": "caption"}]}],
    }


@pytest.mark.django_db
def test_full_clean_accepts_a_document() -> None:
    # JSONField.validate json.dumps()es the value, and a TipTapValue is not
    # JSON-serializable — every non-empty document used to fail here.
    article = Article(title="t", body="b", document=TipTapValue.from_stored({"doc": DOC}))
    article.full_clean()


@pytest.mark.django_db
def test_full_clean_accepts_none_and_empty() -> None:
    Article(title="t", body="b", document=None).full_clean()
    Article(title="t", body="b", document=TipTapValue.from_stored({})).full_clean()


def test_validate_leaves_an_unset_value_to_django() -> None:
    # An unset value is null/blank handling, not document validation — full_clean
    # skips a blank field entirely, so this is checked at the field.
    TipTapJSONField(null=True, blank=True).validate(None, None)
    with pytest.raises(ValidationError):
        TipTapJSONField().validate(None, None)


@pytest.mark.django_db
def test_full_clean_accepts_a_plain_mapping() -> None:
    # A programmatic write can assign the stored mapping rather than a TipTapValue.
    Article(title="t", body="b", document={"doc": DOC, "html": "<p>hi</p>"}).full_clean()


@pytest.mark.django_db
def test_full_clean_rejects_a_non_serializable_document() -> None:
    # The JSONField contract still holds: what cannot reach the column is invalid.
    article = Article(title="t", body="b", document={"doc": {"type": object()}})
    with pytest.raises(ValidationError) as exc:
        article.full_clean()
    assert "document" in exc.value.message_dict


@pytest.mark.django_db
def test_model_form_round_trips_a_document() -> None:
    form = ArticleForm(data={"title": "t", "body": "b", "document": STORED})
    assert form.is_valid(), form.errors
    article = form.save()
    reloaded = Article.objects.get(pk=article.pk)
    assert reloaded.document.doc == DOC
    assert reloaded.document.html == "<p>hi</p>"


@pytest.mark.django_db
def test_model_form_rejects_an_unknown_node_type() -> None:
    # The renderer would flatten the wrapper into its text content on save, so
    # the document is refused rather than silently stripped.
    data = json.dumps({"doc": _unknown_node_doc("youtubeEmbed")})
    form = ArticleForm(data={"title": "t", "body": "b", "document": data})
    assert not form.is_valid()
    assert "youtubeEmbed" in form.errors["document"][0]


@pytest.mark.django_db
def test_full_clean_rejects_an_unknown_mark_type() -> None:
    doc = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "x", "marks": [{"type": "sparkle"}]}],
            }
        ],
    }
    article = Article(title="t", body="b", document=TipTapValue.from_stored({"doc": doc}))
    with pytest.raises(ValidationError) as exc:
        article.full_clean()
    assert "sparkle" in exc.value.message_dict["document"][0]


@pytest.mark.django_db
@override_settings(TIPTAP_EXTRA_EXTENSIONS=["callout"])
def test_full_clean_accepts_a_declared_extension_type() -> None:
    # The documented custom-extension recipe: register it in JS, declare the name
    # in TIPTAP_EXTRA_EXTENSIONS. Declared types are the project's to render.
    article = Article(
        title="t", body="b", document=TipTapValue.from_stored({"doc": _unknown_node_doc("callout")})
    )
    article.full_clean()


@pytest.mark.django_db
def test_full_clean_tolerates_malformed_document_members() -> None:
    # Structural junk is the renderer's problem (it degrades to text); the
    # vocabulary check must not trip over it or mistake it for an unknown type.
    doc = {
        "type": "doc",
        "content": ["oops", {"marks": "not-a-list"}, {"marks": ["x", {"type": 7}], "type": 7}],
    }
    Article(title="t", body="b", document=TipTapValue.from_stored({"doc": doc})).full_clean()


def test_vocabulary_walk_survives_a_document_deeper_than_the_stack() -> None:
    # Far past sys.getrecursionlimit(): the walk is iterative, so a deep document
    # reports its unknown type instead of raising RecursionError.
    doc: dict[str, object] = {"type": "sparkle"}
    for _ in range(5000):
        doc = {"type": "blockquote", "content": [doc]}
    assert _unknown_types(doc, _RENDERABLE_NODE_TYPES, _RENDERABLE_MARK_TYPES) == {"sparkle"}


def test_renderable_vocabulary_matches_the_renderer() -> None:
    # Drift guard: every declared node type must survive render_doc as a wrapper
    # of its own (doc is the exception — it renders as its children by design).
    for kind in _RENDERABLE_NODE_TYPES - {"doc", "text"}:
        node = {"type": kind, "content": [{"type": "text", "text": "x"}]}
        assert render_doc({"type": "doc", "content": [node]}) != "x", kind
    for kind in _RENDERABLE_MARK_TYPES:
        marked = {"type": "text", "text": "x", "marks": [{"type": kind, "attrs": {"color": "red"}}]}
        assert render_doc({"type": "doc", "content": [marked]}) != "x", kind


def test_the_field_vocabulary_covers_everything_the_renderer_handles() -> None:
    """The reverse of the drift guard above: a type the renderer gains, this set lacks.

    The field cannot import the renderer's vocabulary -- ``render_doc`` dispatches
    through an ``if kind == ...`` chain rather than a table -- so the two lists are
    maintained separately. The sibling guard renders every *declared* type and proves
    it survives, which catches a name typed into this set wrongly. It cannot catch the
    other direction: a node the renderer learns to render, that this set still rejects,
    would fail every save of a document containing it. This reads the comparisons out
    of the renderer's source and asserts nothing is missing here.
    """
    import ast
    import importlib
    import inspect

    renderer = importlib.import_module("django_tiptap_editor.utils.render_doc")

    tree = ast.parse(inspect.getsource(renderer))
    handled = {
        node.comparators[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Compare)
        and isinstance(node.left, ast.Name)
        and node.left.id == "kind"
        and isinstance(node.ops[0], ast.Eq)
        and isinstance(node.comparators[0], ast.Constant)
        and isinstance(node.comparators[0].value, str)
    }
    handled |= set(renderer._SIMPLE_MARKS)
    declared = _RENDERABLE_NODE_TYPES | _RENDERABLE_MARK_TYPES
    assert handled - declared == set(), (
        f"the renderer handles {sorted(handled - declared)}, which the field rejects"
    )
