from __future__ import annotations

from django_tiptap_editor.utils.escape_html import escape_html


def test_escapes_markup_characters() -> None:
    assert escape_html("a & b <c> d") == "a &amp; b &lt;c&gt; d"


def test_leaves_quotes_alone_in_text() -> None:
    assert escape_html('it\'s a "quote"') == 'it\'s a "quote"'


def test_escapes_the_double_quote_in_an_attribute_value() -> None:
    assert escape_html('a"b', quote=True) == "a&quot;b"


def test_leaves_the_apostrophe_alone_in_an_attribute_value() -> None:
    # Inert inside a double-quoted attribute, and rewriting it would change every
    # apostrophe in an author's prose on every save.
    assert escape_html("it's", quote=True) == "it's"
