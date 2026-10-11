"""The ``features`` section of docs/configuration.md is checked, not trusted.

The page restates the feature model for a reader: which names exist, which are
always on, and what each one pulls in. Every one of those is a copy of
``constants``, and a copy is what drifts. So this reads each marked region out of
the page and compares it with the table it describes, and runs the page's own
example through the validator and the resolver.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from django_tiptap_editor.constants import BUILTIN_EXTENSIONS, FEATURE_CORE, FEATURE_DEPENDENCIES
from django_tiptap_editor.utils.resolve_features import resolve_features
from django_tiptap_editor.utils.validate_config import validate_config

_PAGE = Path(__file__).resolve().parent.parent / "docs" / "configuration.md"
_NAME = re.compile(r"`(\w+)`")
_PYTHON_BLOCK = re.compile(r"```python\n(.*?)```", re.DOTALL)


def _region(marker: str) -> str:
    matched = re.search(
        rf"<!-- features:{marker} -->(.*?)<!-- /features:{marker} -->",
        _PAGE.read_text(encoding="utf-8"),
        re.DOTALL,
    )
    assert matched is not None, f"configuration.md lost its features:{marker} region"
    return matched[1]


def _table_rows(marker: str) -> list[list[str]]:
    """Each body row of the marked table, as the names in each cell."""
    rows = [line for line in _region(marker).strip().splitlines() if line.startswith("|")]
    return [[cell.strip() for cell in row.strip("|").split("|")] for row in rows[2:]]


def test_the_grouped_names_are_every_feature_once() -> None:
    names = [name for _, cell in _table_rows("groups") for name in _NAME.findall(cell)]
    assert sorted(names) == sorted(BUILTIN_EXTENSIONS - FEATURE_CORE)


def test_the_always_on_list_is_the_core() -> None:
    assert set(_NAME.findall(_region("core"))) == FEATURE_CORE


def test_the_dependency_table_is_the_dependency_map() -> None:
    documented = {
        _NAME.findall(listing)[0]: sorted(_NAME.findall(pulls))
        for listing, pulls in _table_rows("dependencies")
    }
    assert documented == {name: sorted(deps) for name, deps in FEATURE_DEPENDENCIES.items()}


def test_the_email_example_validates_and_leaves_out_headings_and_tables() -> None:
    blocks = [
        block for block in _PYTHON_BLOCK.findall(_PAGE.read_text()) if "# An email body" in block
    ]
    assert len(blocks) == 1
    call = ast.parse(blocks[0]).body[0]
    assert isinstance(call, ast.Expr)
    assert isinstance(call.value, ast.Call)
    config = ast.literal_eval(call.value.keywords[0].value)
    assert validate_config(config) is config
    resolved = resolve_features(config)
    assert resolved is not None
    assert {"listItem", "hardBreak", "link"} <= resolved
    assert not {"heading", "table", "image", "textStyle"} & resolved
