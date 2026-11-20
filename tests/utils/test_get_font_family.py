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


@pytest.mark.parametrize(
    "value",
    [
        "a ,b",
        "a\t,\tb",
        "var(--a ,b)",
        "var(--a, b ,c)",
        "var(--a, b )",
        "var(--a,b)",
        "var(--a, b)",
        "var(--a,\n b)",
        "var(--a,b ),c",
        "var(--a) ,b",
        "var(--a)\f,\rb",
    ],
)
def test_keeps_ascii_whitespace_around_commas_and_inside_var(value: str) -> None:
    assert get_font_family(value) == value


@pytest.mark.parametrize(
    "value",
    [
        "var(--)",
        "var(-x)",
        "var(-)",
        "Var(--a)",
        "xvar(--a)",
        "var (--a)",
        "var(--a b)",
        "var(--a))",
        "var--a)",
        "ar(--a)",
        "vxr(--a)",
        "vax(--a)",
        "va(--a)",
        "var(--a ,)",
        "var(--a, ,b)",
    ],
)
def test_refuses_a_malformed_var(value: str) -> None:
    assert get_font_family(value) == ""


@pytest.mark.parametrize("value", ["Font.Name", "a.b, serif", "'Font.Name'x", "var(--a, b.c)"])
def test_refuses_a_dot_in_a_bare_word(value: str) -> None:
    assert get_font_family(value) == ""


@pytest.mark.parametrize("value", ["Font#Name", "#fff", "a, b#", "var(--a, b#c)"])
def test_refuses_a_hash(value: str) -> None:
    assert get_font_family(value) == ""


@pytest.mark.parametrize("value", ["Font%Name", "100%", "a, b%", "var(--a, b%c)"])
def test_refuses_a_percent_sign(value: str) -> None:
    assert get_font_family(value) == ""


_NON_ASCII_SPACES = ["\x0b", "\x1c", "\x85", "\xa0", " ", " ", " ", " ", " ", "　"]


@pytest.mark.parametrize("space", _NON_ASCII_SPACES)
@pytest.mark.parametrize(
    "template",
    ["a{s},b", "a,{s}b", "var(--a{s},b)", "var(--a,{s}b)", "var(--a, b{s})", "a, var(--b){s},c"],
)
def test_refuses_non_ascii_whitespace_around_a_separator(space: str, template: str) -> None:
    assert get_font_family(template.format(s=space)) == ""


@pytest.mark.parametrize("space", _NON_ASCII_SPACES)
@pytest.mark.parametrize("template", ["{s}Arial", "Arial{s}", "{s}var(--a){s}"])
def test_refuses_non_ascii_whitespace_at_either_end(space: str, template: str) -> None:
    assert get_font_family(template.format(s=space)) == ""


@pytest.mark.parametrize("value", [" Arial", "Arial\t", "\r\n\fArial, serif \n"])
def test_strips_ascii_whitespace_at_either_end(value: str) -> None:
    assert get_font_family(value) == value.strip(" \t\r\n\f")
