from __future__ import annotations

import pytest

from django_tiptap_editor.utils.get_css_value import get_css_value


@pytest.mark.parametrize(
    "value",
    ["10px", "  50%  ", "rgb(255, 0, 0)", "Arial, sans-serif", "1px solid #ccc"],
)
def test_keeps_a_simple_value(value: str) -> None:
    assert get_css_value(value) == value.strip()


@pytest.mark.parametrize(
    "value",
    ["", "   ", "url(javascript:alert(1))", "red; position: fixed", "expression(x)", 5, None],
)
def test_refuses_anything_else(value: object) -> None:
    assert get_css_value(value) == ""
