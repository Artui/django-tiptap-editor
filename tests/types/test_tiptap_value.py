from __future__ import annotations

from django.utils.safestring import SafeString

from django_tiptap_editor.types.tiptap_value import TipTapValue

DOC = {"type": "doc", "content": [{"type": "paragraph"}]}


def test_from_stored_envelope() -> None:
    value = TipTapValue.from_stored({"doc": DOC, "html": "<p></p>"})
    assert value.doc == DOC
    assert value.html == "<p></p>"
    assert isinstance(value.html, SafeString)


def test_from_stored_bare_doc() -> None:
    value = TipTapValue.from_stored(DOC)
    assert value.doc == DOC
    assert value.html == ""


def test_from_stored_non_dict() -> None:
    value = TipTapValue.from_stored(None)
    assert value.doc == {}
    assert value.html == ""


def test_from_stored_coerces_non_dict_doc() -> None:
    value = TipTapValue.from_stored({"doc": "oops", "html": 5})
    assert value.doc == {}
    assert value.html == "5"


def test_to_stored_roundtrips() -> None:
    value = TipTapValue.from_stored({"doc": DOC, "html": "<p>x</p>"})
    assert value.to_stored() == {"doc": DOC, "html": "<p>x</p>"}


def test_str_and_html_are_the_safe_mirror() -> None:
    value = TipTapValue(doc=DOC, html=SafeString("<p>x</p>"))
    assert str(value) == "<p>x</p>"
    assert value.__html__() == "<p>x</p>"
