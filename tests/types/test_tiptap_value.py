from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.template import Context, Template
from django.utils.safestring import SafeString

from django_tiptap_editor.types.tiptap_value import TipTapValue

DOC = {"type": "doc", "content": [{"type": "paragraph"}]}
PAYLOAD = "<img src=x onerror=alert(document.cookie)>"


def test_from_stored_envelope() -> None:
    value = TipTapValue.from_stored({"doc": DOC, "html": "<p></p>"})
    assert value.doc == DOC
    assert value.html == "<p></p>"
    assert isinstance(value.html, SafeString)


def test_from_stored_bare_doc() -> None:
    value = TipTapValue.from_stored(DOC)
    assert value.doc == DOC
    assert value.html == ""


def test_from_stored_rejects_a_non_mapping() -> None:
    with pytest.raises(ValidationError, match="bare ProseMirror doc mapping"):
        TipTapValue.from_stored(None)


def test_from_stored_rejects_html_assigned_as_a_string() -> None:
    # The migration case: assigning a legacy HTML column to a JSON field used to
    # persist an empty document for every row without a word of complaint.
    with pytest.raises(ValidationError, match="HTML is not converted on assignment"):
        TipTapValue.from_stored("<p>my content</p>")


def test_from_stored_rejects_a_list() -> None:
    with pytest.raises(ValidationError):
        TipTapValue.from_stored([{"type": "paragraph"}])


def test_from_stored_rejects_a_non_mapping_doc() -> None:
    with pytest.raises(ValidationError):
        TipTapValue.from_stored({"doc": "oops", "html": ""})


def test_from_stored_rejects_a_non_string_mirror() -> None:
    with pytest.raises(ValidationError, match="must be a string"):
        TipTapValue.from_stored({"doc": DOC, "html": 5})


def test_to_stored_roundtrips() -> None:
    value = TipTapValue.from_stored({"doc": DOC, "html": "<p>x</p>"})
    assert value.to_stored() == {"doc": DOC, "html": "<p>x</p>"}


def test_str_and_html_are_the_safe_mirror() -> None:
    value = TipTapValue(doc=DOC, html=SafeString("<p>x</p>"))
    assert str(value) == "<p>x</p>"
    assert value.__html__() == "<p>x</p>"


def test_from_stored_sanitizes_the_caller_supplied_mirror() -> None:
    value = TipTapValue.from_stored({"doc": {}, "html": PAYLOAD})
    assert value.html == '<img src="x">'
    assert "onerror" not in Template("{{ v }}").render(Context({"v": value}))


def test_direct_construction_sanitizes_the_mirror_too() -> None:
    # The invariant is on the class, not on one entry point: a value built by
    # hand (or left on form.instance by a ModelForm that failed validation) is
    # marked safe, so it has to be safe however it was built.
    value = TipTapValue(doc=DOC, html=SafeString(PAYLOAD))
    assert value.html == '<img src="x">'
