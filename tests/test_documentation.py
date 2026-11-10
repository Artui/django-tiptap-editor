from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
from django.test import override_settings

from django_tiptap_editor.utils.get_html_schema import get_html_schema
from django_tiptap_editor.utils.sanitize_html import sanitize_html

_PAGE = Path(__file__).resolve().parent.parent / "docs" / "extending.md"
_JS_BLOCK = re.compile(r"```js\n(.*?)```", re.DOTALL)
_PYTHON_BLOCK = re.compile(r"```python\n(.*?)```", re.DOTALL)
_RENDER = re.compile(
    r'renderHTML: \(\{ HTMLAttributes \}\) => \["(?P<tag>\w+)", '
    r'mergeAttributes\(HTMLAttributes, \{ class: "(?P<cls>[\w-]+)" \}\), 0\]'
)
_PARSE = re.compile(r'parseHTML: \(\) => \[\{ tag: "(?P<selector>[\w.-]+)" \}\]')


def _callout_source() -> str:
    blocks = [
        block
        for block in _JS_BLOCK.findall(_PAGE.read_text())
        if 'registerExtension("callout"' in block
    ]
    assert len(blocks) == 1, "extending.md should register the callout extension exactly once"
    return blocks[0]


def _declared_settings() -> list[object]:
    """Every ``TIPTAP_EXTRA_EXTENSIONS`` the page assigns that names the callout."""
    found: list[object] = []
    for block in _PYTHON_BLOCK.findall(_PAGE.read_text()):
        for node in ast.walk(ast.parse(block)):
            if isinstance(node, ast.Assign) and [
                getattr(target, "id", None) for target in node.targets
            ] == ["TIPTAP_EXTRA_EXTENSIONS"]:
                value = ast.literal_eval(node.value)
                if "callout" in value:
                    found.append(value)
    return found


def _rendered_markup() -> tuple[str, str]:
    """The markup the documented extension writes, and the text inside it."""
    matched = _RENDER.search(_callout_source())
    assert matched is not None, "the callout's renderHTML no longer has the shape this test reads"
    tag, cls = matched["tag"], matched["cls"]
    return f'<{tag} class="{cls}"><p>Note</p></{tag}>', "<p>Note</p>"


def test_the_page_still_carries_what_this_test_reads() -> None:
    # Without this the parametrised tests below pass by finding nothing.
    settings = _declared_settings()

    assert sum(isinstance(value, dict) for value in settings) == 2
    assert sum(isinstance(value, list) for value in settings) == 2


def test_the_callout_parses_back_what_it_renders() -> None:
    # The editor reloads stored markup through parseHTML.
    source = _callout_source()
    rendered = _RENDER.search(source)
    parsed = _PARSE.search(source)
    assert rendered is not None and parsed is not None

    assert parsed["selector"] == f"{rendered['tag']}.{rendered['cls']}"


@pytest.mark.parametrize(
    "declared",
    [value for value in _declared_settings() if isinstance(value, dict)],
    ids=lambda value: "+".join(sorted(value)),
)
def test_a_declared_callout_survives_the_sanitiser(declared: dict[str, object]) -> None:
    markup, _ = _rendered_markup()

    with override_settings(TIPTAP_EXTRA_EXTENSIONS=declared):
        kept = str(sanitize_html(markup, schema=get_html_schema()))

    assert kept == markup


@pytest.mark.parametrize(
    "listed",
    [value for value in _declared_settings() if isinstance(value, list)],
    ids=lambda value: "+".join(value),
)
def test_a_listed_callout_loses_its_wrapper_and_keeps_its_text(listed: list[str]) -> None:
    # The page says the plain-list form warns, naming the extension.
    markup, inner = _rendered_markup()

    with override_settings(TIPTAP_EXTRA_EXTENSIONS=listed):
        with pytest.warns(UserWarning) as warned:
            schema = get_html_schema()
        kept = str(sanitize_html(markup, schema=schema))

    named = {re.search(r"extension '(\w+)' does not declare", str(w.message))[1] for w in warned}
    assert named == set(listed)
    assert kept == inner
