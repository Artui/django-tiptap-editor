from __future__ import annotations

import pytest

from django_tiptap_editor.utils.sanitize_doc import sanitize_doc


def _link(href: str) -> dict:
    return {"type": "text", "text": "x", "marks": [{"type": "link", "attrs": {"href": href}}]}


def test_non_dict_returned_unchanged() -> None:
    assert sanitize_doc(None) is None
    assert sanitize_doc("text") == "text"


def test_keeps_allowed_link_href() -> None:
    node = {
        "type": "text",
        "text": "x",
        "marks": [{"type": "link", "attrs": {"href": "https://ok"}}],
    }
    assert sanitize_doc(node)["marks"] == node["marks"]


def test_drops_disallowed_link_href() -> None:
    node = {
        "type": "text",
        "text": "x",
        "marks": [{"type": "link", "attrs": {"href": "javascript:alert(1)"}}],
    }
    assert sanitize_doc(node)["marks"] == []


def test_keeps_relative_link_and_other_marks() -> None:
    node = {
        "type": "text",
        "text": "x",
        "marks": [
            {"type": "bold"},
            {"type": "link", "attrs": {"href": "/relative"}},
            {"type": "link"},  # no attrs → no scheme → allowed
            "not-a-dict",  # tolerated, kept
        ],
    }
    assert sanitize_doc(node)["marks"] == node["marks"]


def test_blanks_disallowed_image_src() -> None:
    node = {"type": "image", "attrs": {"src": "javascript:alert(1)", "alt": "a"}}
    out = sanitize_doc(node)
    assert out["attrs"]["src"] == ""
    assert out["attrs"]["alt"] == "a"


def test_keeps_allowed_and_data_image_src() -> None:
    https = {"type": "image", "attrs": {"src": "https://img/x.png"}}
    data = {"type": "image", "attrs": {"src": "data:image/png;base64,AAAA"}}
    assert sanitize_doc(https)["attrs"]["src"] == "https://img/x.png"
    assert sanitize_doc(data)["attrs"]["src"].startswith("data:")


def test_image_without_attrs_is_untouched() -> None:
    node = {"type": "image"}
    assert sanitize_doc(node) == {"type": "image"}


def test_recurses_into_content() -> None:
    doc = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "x",
                        "marks": [{"type": "link", "attrs": {"href": "javascript:x"}}],
                    },
                    {"type": "image", "attrs": {"src": "vbscript:x"}},
                ],
            }
        ],
    }
    out = sanitize_doc(doc)
    para = out["content"][0]["content"]
    assert para[0]["marks"] == []
    assert para[1]["attrs"]["src"] == ""


def test_custom_protocol_allowlist() -> None:
    node = {"type": "text", "marks": [{"type": "link", "attrs": {"href": "ftp://host"}}]}
    assert sanitize_doc(node, link_protocols=("ftp",))["marks"] == node["marks"]


@pytest.mark.parametrize(
    "href",
    [
        "java\nscript:alert(1)",  # embedded newline
        "java\tscript:alert(1)",  # embedded tab
        "jav\rascript:alert(1)",  # embedded carriage return
        "\x01javascript:alert(1)",  # leading C0 control
        "  javascript:alert(1)",  # leading spaces
        "JaVaScRiPt:alert(1)",  # mixed case
        "\x0cJAVA\nSCRIPT:x",  # form-feed + newline, mixed case
    ],
)
def test_drops_javascript_href_hidden_by_whitespace_or_control_chars(href: str) -> None:
    # A browser strips whitespace/control chars while resolving the URL, so these
    # all execute as ``javascript:`` on click — the scheme must be seen and dropped.
    assert sanitize_doc(_link(href))["marks"] == []


def test_blanks_image_src_scheme_hidden_by_whitespace() -> None:
    node = {"type": "image", "attrs": {"src": "java\nscript:alert(1)"}}
    assert sanitize_doc(node)["attrs"]["src"] == ""


def test_keeps_entity_and_percent_encoded_forms_verbatim() -> None:
    # These carry no literal scheme (``&``/``%`` prefix), so sanitize keeps them;
    # render_doc's HTML-escaping is what neutralizes them on output — the browser
    # never re-decodes an escaped attribute into an executable scheme.
    for href in ["&#106;avascript:alert(1)", "%6aavascript:alert(1)"]:
        assert sanitize_doc(_link(href))["marks"] == _link(href)["marks"]
