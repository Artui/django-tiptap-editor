"""nh3 as an outside opinion on what ``sanitize_html`` lets through.

nh3 (the Rust ammonia sanitiser) is a development dependency only: the package
itself depends on Django alone. Seeded fragments of hostile markup are cleaned by
``sanitize_html``, and every element in the result is then cleaned again, on its
own, by nh3 configured with the same allowlist. Every attribute we kept must
survive nh3, every style declaration we kept must be one nh3 keeps, and every URL
we kept must come back from nh3 unchanged. A failure means our filtering let
through something an independent sanitiser with the same rules would not.

Elements are compared one at a time, not documents, because the two parse
malformed markup differently (nh3 builds an HTML5 tree, ``sanitize_html`` reads
tokens) and a document comparison is dominated by that difference, which says
nothing about what either lets through.

``SANITIZE_ORACLE_CASES`` sets how many fragments a run generates (10,000 by
default, a couple of seconds), and ``SANITIZE_ORACLE_SEED`` the seed, so a
scheduled run can go wider than a pull request does.
"""

from __future__ import annotations

import os
import random
from collections.abc import Callable
from html.parser import HTMLParser

import nh3
import pytest

from django_tiptap_editor.types.html_schema import HtmlSchema
from django_tiptap_editor.utils.get_html_schema import get_html_schema
from django_tiptap_editor.utils.sanitize_html import sanitize_html

_CASES = int(os.environ.get("SANITIZE_ORACLE_CASES", "10000"))
_SEED = int(os.environ.get("SANITIZE_ORACLE_SEED", "2"))

_KEPT = [
    "p",
    "a",
    "img",
    "ul",
    "ol",
    "li",
    "blockquote",
    "pre",
    "code",
    "br",
    "hr",
    "h1",
    "h2",
    "strong",
    "em",
    "u",
    "s",
    "sub",
    "sup",
    "span",
    "table",
    "tbody",
    "tr",
    "td",
    "th",
    "colgroup",
    "col",
]
_UNKNOWN = [
    "div",
    "font",
    "b",
    "i",
    "big",
    "small",
    "nobr",
    "svg",
    "math",
    "mtext",
    "textarea",
    "title",
    "noscript",
    "xmp",
    "template",
    "select",
    "option",
    "iframe",
    "noembed",
    "plaintext",
    "style",
    "script",
    "form",
    "button",
]
_URLS = [
    "https://e.test/x",
    "/rel",
    "#frag",
    "javascript:alert(1)",
    "java\tscript:alert(1)",
    "java&#x09;script:alert(1)",
    "javascript&colon;alert(1)",
    " javascript:alert(1)",
    "JaVaScRiPt:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "data:image/png;base64,AAAA",
    "vbscript:x",
    "mailto:a@e.test",
    "tel:123",
    "&#106;avascript:alert(1)",
    "https://e.test/?a=1&lt=2",
]
_STYLES = [
    "color: red",
    "text-align: center",
    "position: fixed",
    "background-image: url(javascript:alert(1))",
    "font-size: 12px; behavior: url(x)",
    "margin: expression(alert(1))",
]
_ATTRIBUTES = [
    "href",
    "src",
    "style",
    "onclick",
    "onerror",
    "class",
    "title",
    "target",
    "rel",
    "colspan",
    "start",
    "alt",
    "id",
]
_TEXT = ["x", "a & b", "&amp;", "&lt;script&gt;", "&nbsp;", "&copy", "&#0;", "1 < 2", "\n"]
_TEXT += ["'q'", '"d"', "&ltimg", "</", "<<"]
# Character references a parser may leave unfinished. From Python 3.14 a decimal
# one running into a hex letter hands the sanitiser the rest of the fragment as
# its name, so these are what holds that path.
_TEXT += ["&#1a", "&#9F", "&#x", "&#", "&#X1g"]
_JUNK = ["<!-- c -->", "<!--", "-->", "<![CDATA[x]]>", "<?pi?>", "</b>", "</p>", "</td>"]
_JUNK += ["<!x>", "</ x>", '"', "'", "<", ">", "=", "/>"]


def _attribute(rng: random.Random) -> str:
    name = rng.choice(_ATTRIBUTES)
    if name in {"href", "src"}:
        value = rng.choice(_URLS)
    elif name == "style":
        value = rng.choice(_STYLES)
    elif name == "target":
        value = rng.choice(["_blank", "_self", "evil"])
    elif name == "rel":
        value = rng.choice(["opener", "noopener", "nofollow"])
    else:
        value = rng.choice(["1", "x", "alert(1)", ""])
    quote = rng.choice(['"', "'", ""])
    if not quote and (" " in value or not value):
        quote = '"'
    return f" {name}={quote}{value}{quote}"


def _fragment(rng: random.Random) -> str:
    parts = []
    for _ in range(rng.randint(3, 30)):
        roll = rng.random()
        if roll < 0.35:
            tag = rng.choice(_KEPT if rng.random() < 0.7 else _UNKNOWN)
            attributes = "".join(_attribute(rng) for _ in range(rng.randint(0, 3)))
            parts.append(f"<{tag}{attributes}>")
        elif roll < 0.55:
            parts.append(f"</{rng.choice(_KEPT + _UNKNOWN)}>")
        elif roll < 0.85:
            parts.append(rng.choice(_TEXT))
        else:
            parts.append(rng.choice(_JUNK))
    return "".join(parts)


class _Elements(HTMLParser):
    """Every start tag of a document, in order, with its attributes."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: list[tuple[str, list[tuple[str, str]]]] = []

    def set_cdata_mode(self, *args: object, **kwargs: object) -> None:
        # Read every start tag as one, whatever this Python treats as raw text.
        ...

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.elements.append((tag, [(name, value or "") for name, value in attrs]))


def _elements(html: str) -> list[tuple[str, list[tuple[str, str]]]]:
    parser = _Elements()
    parser.feed(html)
    parser.close()
    return parser.elements


# What an element needs around it to survive an HTML5 parse on its own.
_CONTEXT = {
    "td": ("<table><tbody><tr>", "</tr></tbody></table>"),
    "th": ("<table><tbody><tr>", "</tr></tbody></table>"),
    "tr": ("<table><tbody>", "</tbody></table>"),
    "tbody": ("<table>", "</table>"),
    "colgroup": ("<table>", "</table>"),
    "col": ("<table><colgroup>", "</colgroup></table>"),
    "li": ("<ul>", "</ul>"),
}


def _declarations(style: str) -> set[str]:
    return {part.partition(":")[0].strip().lower() for part in style.split(";") if ":" in part}


def _nh3(schema: HtmlSchema) -> Callable[[str, str], str]:
    """nh3 with ``schema``'s allowlist, for an element named by the first argument."""
    tags = set(schema.tags)
    attributes = {
        tag: set(schema.attributes(tag)) | ({"style"} if schema.style_properties(tag) else set())
        for tag in tags
    }
    properties = set().union(*schema.styles.values())

    def clean(tag: str, html: str) -> str:
        # The image protocols govern src and the link ones href; nh3 takes one
        # list per call, so each element gets the list for the URL it carries.
        schemes = schema.image_protocols if tag == "img" else schema.link_protocols
        return nh3.clean(
            html,
            tags=tags,
            attributes=attributes,
            url_schemes=set(schemes),
            # The sanitiser writes the rel it computes, so nh3 must not add one.
            link_rel=None,
            filter_style_properties=properties,
            clean_content_tags={"script", "style"},
        )

    return clean


def _refused_by_nh3(ours: str, clean: Callable[[str, str], str]) -> list[str]:
    """What we kept on each element of ``ours`` that nh3 refuses on it alone."""
    refused = []
    for tag, attrs in _elements(ours):
        quoted = "".join(
            f' {name}="{value.replace("&", "&amp;").replace(chr(34), "&quot;")}"'
            for name, value in attrs
        )
        before, after = _CONTEXT.get(tag, ("", ""))
        theirs = _elements(clean(tag, f"{before}<{tag}{quoted}>x</{tag}>{after}"))
        allowed = next((dict(a) for t, a in theirs if t == tag), None)
        if allowed is None:
            refused.append(f"<{tag}>")
            continue
        for name, value in attrs:
            if name not in allowed:
                refused.append(f"{tag}[{name}]")
            elif name == "style" and not _declarations(value) <= _declarations(allowed[name]):
                refused.append(f"{tag}[style] {value!r}, nh3 kept {allowed[name]!r}")
            elif name in {"href", "src"} and value != allowed[name]:
                refused.append(f"{tag}[{name}] {value!r}, nh3 kept {allowed[name]!r}")
    return refused


_SCHEMAS = {
    "unrestricted": lambda: get_html_schema(),
    "restricted": lambda: get_html_schema({"features": ["bold", "italic", "link", "hardBreak"]}),
}


@pytest.mark.parametrize("schema_name", _SCHEMAS)
def test_nothing_sanitize_html_keeps_is_refused_by_nh3(schema_name: str) -> None:
    schema = _SCHEMAS[schema_name]()
    clean = _nh3(schema)
    rng = random.Random(f"{_SEED}:{schema_name}")
    failures = []
    for _ in range(_CASES):
        html = _fragment(rng)
        refused = _refused_by_nh3(str(sanitize_html(html, schema=schema)), clean)
        if refused:
            failures.append((html, refused))
    assert not failures, f"{len(failures)} of {_CASES}; first: {failures[:3]}"


# The oracle is only evidence if it can fail: markup no sanitiser touched, fed
# straight to the comparison, must be refused for each kind of thing it checks.
@pytest.mark.parametrize(
    ("markup", "refused"),
    [
        ('<a href="javascript:alert(1)">x</a>', "a[href]"),
        ('<img src="vbscript:x">', "img[src]"),
        ('<p style="position: fixed">x</p>', "p[style]"),
        ('<table><tbody><tr><td onclick="x()">x</td></tr></tbody></table>', "td[onclick]"),
        ("<iframe>x</iframe>", "<iframe>"),
    ],
)
def test_the_comparison_refuses_what_nh3_would(markup: str, refused: str) -> None:
    found = _refused_by_nh3(markup, _nh3(get_html_schema()))
    assert any(item.startswith(refused) for item in found), found
