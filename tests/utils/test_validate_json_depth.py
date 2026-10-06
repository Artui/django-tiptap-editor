from __future__ import annotations

from collections.abc import Callable

import pytest
from django.core.exceptions import ValidationError

from django_tiptap_editor.constants import MAX_DOCUMENT_DEPTH, MAX_JSON_DEPTH
from django_tiptap_editor.utils.sanitize_doc import sanitize_doc
from django_tiptap_editor.utils.validate_json_depth import validate_json_depth

_REFUSED = f"nests values deeper than the maximum of {MAX_JSON_DEPTH} levels"


def _arrays(depth: int, leaf: object = None) -> object:
    """``depth`` nested arrays, the innermost holding ``leaf`` when one is given."""
    value: object = [] if leaf is None else [leaf]
    for _ in range(depth - 1):
        value = [value]
    return value


def _objects(depth: int) -> object:
    value: object = {}
    for _ in range(depth - 1):
        value = {"k": value}
    return value


@pytest.mark.parametrize("nest", [_arrays, _objects], ids=["arrays", "objects"])
def test_a_value_at_the_limit_passes(nest: Callable[[int], object]) -> None:
    validate_json_depth(nest(MAX_JSON_DEPTH))


@pytest.mark.parametrize("nest", [_arrays, _objects], ids=["arrays", "objects"])
def test_a_value_one_level_past_the_limit_is_refused(nest: Callable[[int], object]) -> None:
    with pytest.raises(ValidationError, match=_REFUSED):
        validate_json_depth(nest(MAX_JSON_DEPTH + 1))


def test_a_scalar_is_not_a_level() -> None:
    # Only objects and arrays nest. A number inside the innermost array leaves
    # the value at the limit, not one past it.
    validate_json_depth(_arrays(MAX_JSON_DEPTH, leaf=1))


def test_depth_is_measured_per_branch_not_summed() -> None:
    validate_json_depth({"a": _arrays(MAX_JSON_DEPTH - 1), "b": _objects(MAX_JSON_DEPTH - 1)})


def test_a_value_far_past_the_stack_is_refused_rather_than_a_recursion_error() -> None:
    # A recursive walk would raise RecursionError long before a million levels,
    # which is the failure this check exists to turn into a field error.
    with pytest.raises(ValidationError, match=_REFUSED):
        validate_json_depth(_arrays(1_000_000))


def _at_the_node_limit(extra: int = 0) -> dict:
    """The deepest document ``sanitize_doc`` accepts, plus ``extra`` levels.

    Its innermost node carries a mark with attrs and its parent an array
    attribute, the deepest shapes the editor writes.
    """
    node: dict = {
        "type": "text",
        "text": "x",
        "marks": [{"type": "link", "attrs": {"href": "https://a.b"}}],
    }
    for _ in range(MAX_DOCUMENT_DEPTH - 2 + extra):
        node = {"type": "tableCell", "attrs": {"colwidth": [120]}, "content": [node]}
    return {"type": "doc", "content": [node]}


def test_the_bound_leaves_room_above_the_deepest_document_the_node_limit_accepts() -> None:
    deepest = _at_the_node_limit()
    sanitize_doc(deepest)
    with pytest.raises(ValidationError, match="nests deeper"):
        sanitize_doc(_at_the_node_limit(extra=1))
    validate_json_depth(deepest)
    # A node costs two levels, so the deepest document is 2 * MAX_DOCUMENT_DEPTH
    # + 2 deep, which leaves nearly as many levels again below the bound.
    room = MAX_JSON_DEPTH - (2 * MAX_DOCUMENT_DEPTH + 2)
    validate_json_depth(_arrays(room, leaf=deepest))
    with pytest.raises(ValidationError, match=_REFUSED):
        validate_json_depth(_arrays(room + 1, leaf=deepest))
