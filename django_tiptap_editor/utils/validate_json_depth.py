"""Refuse a JSON value nested deeper than ``MAX_JSON_DEPTH`` (internal helper)."""

from __future__ import annotations

from django.core.exceptions import ValidationError

from django_tiptap_editor.constants import MAX_JSON_DEPTH


def validate_json_depth(value: object) -> None:
    """Raise ``ValidationError`` if ``value`` nests deeper than ``MAX_JSON_DEPTH``.

    Every object and array counts, wherever it sits. ``sanitize_doc`` bounds only
    ``content``, so an array nested a few hundred levels inside a node's
    ``attrs`` passed it, and ``json.dumps`` -- which Django's ``JSONField`` runs
    in ``validate`` and again on save -- then raised RecursionError on it. The
    walk is iterative, so the check cannot fail the way it guards against.
    """
    stack: list[tuple[object, int]] = [(value, 1)]
    while stack:
        item, depth = stack.pop()
        if not isinstance(item, (dict, list)):
            continue
        if depth > MAX_JSON_DEPTH:
            raise ValidationError(
                f"TipTap document nests values deeper than the maximum of {MAX_JSON_DEPTH} levels."
            )
        children = item.values() if isinstance(item, dict) else item
        stack.extend((child, depth + 1) for child in children)
