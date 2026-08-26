from __future__ import annotations

import pytest

from django_tiptap_editor.constants import DEFAULT_LINK_PROTOCOLS
from django_tiptap_editor.utils.is_allowed_url import is_allowed_url


@pytest.mark.parametrize(
    "url",
    ["https://example.test", "MAILTO:a@b.test", "/relative", "#anchor", "", None, 5],
)
def test_allowed(url: object) -> None:
    assert is_allowed_url(url, DEFAULT_LINK_PROTOCOLS)


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "JaVaScRiPt:alert(1)",
        "java\tscript:alert(1)",
        "  javascript:alert(1)",
        "java\x00script:alert(1)",
        "vbscript:x",
        "data:text/html,<script>",
    ],
)
def test_refused(url: str) -> None:
    assert not is_allowed_url(url, DEFAULT_LINK_PROTOCOLS)
