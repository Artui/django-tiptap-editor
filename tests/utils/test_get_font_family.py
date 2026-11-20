from __future__ import annotations

import pytest

from django_tiptap_editor.utils.get_font_family import get_font_family


@pytest.mark.parametrize(
    "value",
    [
        "Arial, sans-serif",
        "'Times New Roman', serif",
        "'Courier New', monospace",
        '"Times New Roman", Times, serif',
        "Segoe UI",
        '"Expression Pro", "url(x)"',
    ],
)
def test_keeps_a_safe_list_as_written(value: str) -> None:
    assert get_font_family(f"  {value}\t") == value


@pytest.mark.parametrize(
    "value",
    [
        '"a;b"',
        '"a"b"',
        "'a'b'",
        '"a\\"b"',
        "\\75 rl(x)",
        '"unterminated',
        "url(x)",
        "expression(x)",
        "'a' 'b'",
        "a,,b",
        "a,",
        "a\nb",
        '"a\nb"',
        "",
        "   ",
        '"a<b"',
    ],
)
def test_refuses_an_unsafe_list(value: str) -> None:
    assert get_font_family(value) == ""


def test_refuses_a_non_string() -> None:
    assert get_font_family(3) == ""
