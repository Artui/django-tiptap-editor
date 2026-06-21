from __future__ import annotations

from django_tiptap_editor.utils.sanitize_doc import sanitize_doc


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
