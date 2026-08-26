"""The tag/attribute allowlist the server-side HTML sanitiser enforces."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from django_tiptap_editor.constants import DEFAULT_IMAGE_PROTOCOLS, DEFAULT_LINK_PROTOCOLS


@dataclass(frozen=True)
class HtmlSchema:
    """What the editor may emit: tags, their attributes, their style properties.

    Built by ``get_html_schema`` from the vocabularies of the extensions the
    editor mounts, so it is a description of the editor's own output rather than
    a second allowlist maintained alongside it. ``sanitize_html`` accepts exactly
    what this describes and unwraps everything else.
    """

    tags: Mapping[str, frozenset[str]]
    styles: Mapping[str, frozenset[str]]
    link_protocols: tuple[str, ...] = DEFAULT_LINK_PROTOCOLS
    image_protocols: tuple[str, ...] = DEFAULT_IMAGE_PROTOCOLS

    def allows(self, tag: str) -> bool:
        """Return whether ``tag`` survives sanitisation at all."""
        return tag in self.tags

    def attributes(self, tag: str) -> frozenset[str]:
        """Return the attribute names allowed on ``tag``."""
        return self.tags.get(tag, frozenset())

    def style_properties(self, tag: str) -> frozenset[str]:
        """Return the inline-style properties allowed on ``tag``."""
        return self.styles.get(tag, frozenset())
