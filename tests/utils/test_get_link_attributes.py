from __future__ import annotations

import pytest

from django_tiptap_editor.utils.get_link_attributes import get_link_attributes


def test_a_document_without_target_or_rel_gets_neither() -> None:
    assert get_link_attributes(None, None) == ("", "")


def test_self_target_is_kept() -> None:
    assert get_link_attributes("_self", None) == ("_self", "")


@pytest.mark.parametrize("target", ["evilframe", "_parent", "_top", 5])
def test_an_unknown_target_is_dropped(target: object) -> None:
    assert get_link_attributes(target, None)[0] == ""


def test_a_blank_target_always_carries_noopener_noreferrer() -> None:
    assert get_link_attributes("_blank", None) == ("_blank", "noopener noreferrer")


def test_the_opener_token_is_replaced_rather_than_kept() -> None:
    assert get_link_attributes("_blank", "opener") == ("_blank", "noopener noreferrer")


def test_known_rel_tokens_survive_alongside_the_forced_pair() -> None:
    assert get_link_attributes("_blank", "nofollow noopener") == (
        "_blank",
        "noopener noreferrer nofollow",
    )


def test_rel_without_a_target_keeps_only_known_tokens() -> None:
    assert get_link_attributes(None, "nofollow opener") == ("", "nofollow")


def test_a_non_string_rel_is_dropped() -> None:
    assert get_link_attributes(None, 5) == ("", "")
