from __future__ import annotations

from django.utils.safestring import SafeString

from django_tiptap_editor.utils.render_doc import render_doc


def _p(*content: dict) -> dict:
    return {"type": "doc", "content": [{"type": "paragraph", "content": list(content)}]}


def _text(text: str, marks: list | None = None) -> dict:
    node = {"type": "text", "text": text}
    if marks is not None:
        node["marks"] = marks
    return node


def test_non_dict_renders_empty() -> None:
    assert render_doc(None) == ""
    assert render_doc("x") == ""


def test_returns_safestring() -> None:
    assert isinstance(render_doc(_p(_text("hi"))), SafeString)


def test_paragraph_and_text_escaped() -> None:
    assert render_doc(_p(_text("a <b> & c"))) == "<p>a &lt;b&gt; &amp; c</p>"


def test_simple_marks_nest_first_outermost() -> None:
    out = render_doc(_p(_text("x", [{"type": "bold"}, {"type": "italic"}])))
    assert out == "<p><strong><em>x</em></strong></p>"


def test_all_simple_marks() -> None:
    for kind, tag in [
        ("underline", "u"),
        ("strike", "s"),
        ("code", "code"),
        ("subscript", "sub"),
        ("superscript", "sup"),
    ]:
        out = render_doc(_p(_text("x", [{"type": kind}])))
        assert out == f"<p><{tag}>x</{tag}></p>"


def test_link_mark_with_and_without_rel_target() -> None:
    assert render_doc(_p(_text("x", [{"type": "link", "attrs": {"href": "https://a"}}]))) == (
        '<p><a href="https://a">x</a></p>'
    )
    out = render_doc(
        _p(
            _text(
                "x",
                [
                    {
                        "type": "link",
                        "attrs": {"href": "https://a", "target": "_blank", "rel": "noopener"},
                    }
                ],
            )
        )
    )
    assert out == '<p><a href="https://a" target="_blank" rel="noopener">x</a></p>'


def test_link_with_whitespace_hidden_scheme_is_dropped() -> None:
    # ``java\nscript:`` resolves to the javascript scheme in a browser; the link
    # mark must be stripped so no <a href> reaches the output at all.
    out = render_doc(_p(_text("x", [{"type": "link", "attrs": {"href": "java\nscript:alert(1)"}}])))
    assert out == "<p>x</p>"


def test_entity_encoded_href_is_html_escaped_not_executable() -> None:
    # Carries no literal scheme, so the mark survives — but the ``&`` is escaped,
    # so the browser can't decode the attribute back into a javascript: scheme.
    out = render_doc(
        _p(_text("x", [{"type": "link", "attrs": {"href": "&#106;avascript:alert(1)"}}]))
    )
    assert out == '<p><a href="&amp;#106;avascript:alert(1)">x</a></p>'


def test_textstyle_builds_span_or_skips() -> None:
    out = render_doc(
        _p(_text("x", [{"type": "textStyle", "attrs": {"color": "#f00", "fontSize": "20px"}}]))
    )
    assert out == '<p><span style="color: #f00; font-size: 20px">x</span></p>'
    # No usable attrs → no span wrapper.
    assert render_doc(_p(_text("x", [{"type": "textStyle", "attrs": {}}]))) == "<p>x</p>"


def test_unknown_and_nondict_marks_pass_through() -> None:
    out = render_doc(_p(_text("x", [{"type": "weird"}, "not-a-dict"])))
    assert out == "<p>x</p>"


def test_text_without_marks_list() -> None:
    assert render_doc(_p({"type": "text", "text": "plain"})) == "<p>plain</p>"


def test_css_injection_is_stripped() -> None:
    # A property-injection / url(javascript:) style value is dropped entirely.
    out = render_doc(
        _p(_text("x", [{"type": "textStyle", "attrs": {"color": "red; position: fixed"}}]))
    )
    assert out == "<p>x</p>"
    out2 = render_doc(
        _p(_text("x", [{"type": "textStyle", "attrs": {"fontFamily": "expression(alert(1))"}}]))
    )
    assert out2 == "<p>x</p>"


def test_block_style_attrs() -> None:
    doc = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "attrs": {
                    "margin": "10px",
                    "marginBlockEnd": "5px",
                    "paddingLeft": "40px",
                    "textAlign": "center",
                },
                "content": [_text("x")],
            }
        ],
    }
    assert render_doc(doc) == (
        '<p style="margin: 10px; margin-block-end: 5px; padding-left: 40px; text-align: center">x</p>'
    )


def test_headings_levels_and_clamp() -> None:
    h2 = {
        "type": "doc",
        "content": [{"type": "heading", "attrs": {"level": 2}, "content": [_text("h")]}],
    }
    assert render_doc(h2) == "<h2>h</h2>"
    bad = {
        "type": "doc",
        "content": [{"type": "heading", "attrs": {"level": 9}, "content": [_text("h")]}],
    }
    assert render_doc(bad) == "<h1>h</h1>"


def test_lists() -> None:
    ul = {
        "type": "doc",
        "content": [
            {"type": "bulletList", "content": [{"type": "listItem", "content": [_p_inner("a")]}]}
        ],
    }
    assert render_doc(ul) == "<ul><li><p>a</p></li></ul>"
    ol = {"type": "doc", "content": [{"type": "orderedList", "attrs": {"start": 3}, "content": []}]}
    assert render_doc(ol) == '<ol start="3"></ol>'
    ol1 = {
        "type": "doc",
        "content": [{"type": "orderedList", "attrs": {"start": 1}, "content": []}],
    }
    assert render_doc(ol1) == "<ol></ol>"


def _p_inner(text: str) -> dict:
    return {"type": "paragraph", "content": [_text(text)]}


def test_blockquote_codeblock_rules_breaks() -> None:
    doc = {
        "type": "doc",
        "content": [
            {"type": "blockquote", "content": [_p_inner("q")]},
            {"type": "codeBlock", "content": [_text("code")]},
            {"type": "horizontalRule"},
            {"type": "paragraph", "content": [_text("a"), {"type": "hardBreak"}, _text("b")]},
        ],
    }
    assert render_doc(doc) == (
        "<blockquote><p>q</p></blockquote><pre><code>code</code></pre><hr><p>a<br>b</p>"
    )


def test_image_attrs_and_protocol() -> None:
    doc = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "image",
                        "attrs": {"src": "https://i/x.png", "alt": "a", "width": "100"},
                    }
                ],
            }
        ],
    }
    assert (
        render_doc(doc)
        == '<p><img src="https://i/x.png" alt="a" width="100" style="width: 100"></p>'
    )


def test_table_rendering() -> None:
    doc = {
        "type": "doc",
        "content": [
            {
                "type": "table",
                "content": [
                    {
                        "type": "tableRow",
                        "content": [
                            {
                                "type": "tableHeader",
                                "attrs": {"colspan": 2},
                                "content": [_p_inner("h")],
                            },
                            {"type": "tableCell", "content": [_p_inner("c")]},
                        ],
                    }
                ],
            }
        ],
    }
    assert render_doc(doc) == (
        '<table><tbody><tr><th colspan="2"><p>h</p></th><td><p>c</p></td></tr></tbody></table>'
    )


def test_children_not_a_list() -> None:
    # A paragraph whose content is missing renders empty.
    assert render_doc({"type": "doc", "content": [{"type": "paragraph"}]}) == "<p></p>"


def test_unknown_node_keeps_content() -> None:
    doc = {"type": "doc", "content": [{"type": "mystery", "content": [_p_inner("kept")]}]}
    assert render_doc(doc) == "<p>kept</p>"


def test_disallowed_link_and_image_protocols_stripped() -> None:
    doc = _p(_text("x", [{"type": "link", "attrs": {"href": "javascript:alert(1)"}}]))
    assert render_doc(doc) == "<p>x</p>"
    img = {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "image", "attrs": {"src": "javascript:x"}}]}
        ],
    }
    assert 'src=""' not in render_doc(img) or "javascript" not in render_doc(img)
    assert "javascript" not in render_doc(img)
