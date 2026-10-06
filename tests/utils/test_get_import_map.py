from __future__ import annotations

import re
from pathlib import Path

from django.test import override_settings

from django_tiptap_editor.constants import GLUE_IMPORT_SPECIFIERS, TIPTAP_VERSION
from django_tiptap_editor.utils.get_import_map import default_import_map, get_import_map


def test_default_pins_every_glue_specifier() -> None:
    mapping = get_import_map()
    assert set(mapping) == set(GLUE_IMPORT_SPECIFIERS)
    assert mapping["@tiptap/core"] == f"https://esm.sh/@tiptap/core@{TIPTAP_VERSION}"


# The glue module external mode serves. esbuild leaves every @tiptap/* import
# as a bare specifier, and the browser refuses to run a module importing a bare
# specifier that no import map entry resolves.
_GLUE = (
    Path(__file__).resolve().parents[2]
    / "django_tiptap_editor"
    / "static"
    / "django_tiptap_editor"
    / "tiptap.glue.esm.js"
)


def test_the_default_map_resolves_exactly_what_the_built_glue_imports() -> None:
    # GLUE_IMPORT_SPECIFIERS is a hand-kept list of what the build externalises.
    # Read the specifiers out of the committed glue instead, so moving an import
    # to another package (as CharacterCount moved to @tiptap/extensions) cannot
    # leave the default map resolving a module the glue no longer asks for while
    # missing the one it does.
    imported = set(re.findall(r'(?:from|import)\s*"(@tiptap/[^"]+)"', _GLUE.read_text("utf-8")))
    assert imported == set(GLUE_IMPORT_SPECIFIERS)


def test_default_import_map_helper_matches() -> None:
    assert get_import_map() == default_import_map()


@override_settings(TIPTAP_IMPORT_MAP={"@tiptap/core": "https://cdn.example/core.js"})
def test_explicit_setting_overrides_default() -> None:
    assert get_import_map() == {"@tiptap/core": "https://cdn.example/core.js"}


@override_settings(TIPTAP_IMPORT_MAP={})
def test_explicit_empty_map_is_respected() -> None:
    assert get_import_map() == {}
