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
        "var(--brand-font)",
        "var(--brand-font, Arial)",
        'var(--x, "Times New Roman", serif)',
        "var(--a), serif",
        "Arial,\n  sans-serif",
        '"Foo, Inc", serif',
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
        "var(x)",
        "var(--a;b)",
        "var(--a, url(x))",
        "var(--a, var(--b))",
        "var(--a",
        "var(--a, expression(x))",
        "var(--a, )",
        "Times\nNew Roman",
    ],
)
def test_refuses_an_unsafe_list(value: str) -> None:
    assert get_font_family(value) == ""


def test_refuses_a_non_string() -> None:
    assert get_font_family(3) == ""


def test_keeps_a_value_with_surrounding_line_breaks() -> None:
    assert get_font_family("Arial\r\n") == "Arial"


@pytest.mark.parametrize(
    "value",
    [
        '"a\\b"',
        "'a\\b'",
        '"\\75 rl(x)"',
        '"a\\", "b url(x) c"',
        "'a;b'",
        '"a<b"',
        "'a<b'",
        '"a>b"',
        "'a>b'",
        '"a\rb"',
        "'a\rb'",
        '"a\nb"',
        "'a\nb'",
    ],
)
def test_refuses_each_character_a_quoted_name_may_not_hold(value: str) -> None:
    assert get_font_family(value) == ""
