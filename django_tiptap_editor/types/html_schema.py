from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from django_tiptap_editor.constants import DEFAULT_IMAGE_PROTOCOLS, DEFAULT_LINK_PROTOCOLS


@dataclass(frozen=True)
class HtmlSchema:
    """What the editor may emit: tags, their attributes, their style properties."""

    tags: Mapping[str, frozenset[str]]
    styles: Mapping[str, frozenset[str]]
    link_protocols: tuple[str, ...] = DEFAULT_LINK_PROTOCOLS
    image_protocols: tuple[str, ...] = DEFAULT_IMAGE_PROTOCOLS
    paragraph_blocks: frozenset[str] = frozenset()

    def allows(self, tag: str) -> bool:
        """Return whether ``tag`` survives sanitisation at all."""
        return tag in self.tags

    def attributes(self, tag: str) -> frozenset[str]:
        """Return the attribute names allowed on ``tag``."""
        return self.tags.get(tag, frozenset())

    def style_properties(self, tag: str) -> frozenset[str]:
        """Return the inline-style properties allowed on ``tag``."""
        return self.styles.get(tag, frozenset())
