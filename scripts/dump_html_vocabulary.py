"""Write the built-in HTML vocabulary where the JS tests can read it.

EXTENSION_HTML_VOCABULARY is the server's statement of what the editor emits:
the sanitiser keeps exactly the tags, attributes and style properties it lists.
Nothing on the Python side can check that statement, because only the editor
knows what it produces, and a Tiptap upgrade can teach an extension to parse and
render something new without any Python file changing. Tiptap 3 did exactly
that for link titles and table-cell alignment, and the editor showed both while
every save stripped them.

So the vocabulary is dumped to js/test/fixtures/html-vocabulary.json, and
js/test/html-vocabulary.test.ts renders every attribute the editor's schema
defines and asserts the output stays inside it. The same file carries the
built-in extension names, which the JS registry restates as BUILTIN_NAMES.

tests/test_js_vocabulary_mirror.py fails while the committed file differs from
a fresh dump, so a vocabulary change cannot land without the JS side reading it.

    uv run python scripts/dump_html_vocabulary.py          # rewrite the fixture
    uv run python scripts/dump_html_vocabulary.py --check  # exit 1 if stale
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from django_tiptap_editor.constants import EXTENSION_HTML_VOCABULARY

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "js" / "test" / "fixtures" / "html-vocabulary.json"


def build() -> dict[str, object]:
    """Return the vocabulary as plain JSON: names, then the per-tag union.

    The union matches what get_html_schema builds for the built-ins, without the
    project's TIPTAP_EXTRA_EXTENSIONS, which describe a consumer's extensions
    rather than this editor.
    """
    attributes: dict[str, set[str]] = {}
    styles: dict[str, set[str]] = {}
    for vocabulary in EXTENSION_HTML_VOCABULARY.values():
        for tag, entry in vocabulary.items():
            attributes.setdefault(tag, set()).update(entry.get("attrs", ()))
            styles.setdefault(tag, set()).update(entry.get("styles", ()))
    return {
        "generatedBy": "scripts/dump_html_vocabulary.py",
        "extensions": sorted(EXTENSION_HTML_VOCABULARY),
        "tags": {
            tag: {"attributes": sorted(attributes[tag]), "styles": sorted(styles[tag])}
            for tag in sorted(attributes)
        },
    }


def render() -> str:
    """Return the fixture's exact bytes, so a byte comparison is the check."""
    return json.dumps(build(), indent=2) + "\n"


def main(argv: list[str]) -> int:
    if argv == ["--check"]:
        return 0 if FIXTURE.read_text(encoding="utf-8") == render() else 1
    FIXTURE.write_text(render(), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
