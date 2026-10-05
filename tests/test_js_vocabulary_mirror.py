"""The JS tests read the current HTML vocabulary, not a stale copy of it.

js/test/html-vocabulary.test.ts checks that everything the editor can emit is
something EXTENSION_HTML_VOCABULARY keeps. It reads the vocabulary from a JSON
fixture, because the JS suite cannot import Python. That check is only as good
as the fixture is current, so this compares the committed file with a fresh
dump on every pull request. The dump is loaded from the script rather than
restated, so there is one definition of the fixture's shape.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

from django_tiptap_editor.constants import EXTENSION_HTML_VOCABULARY

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "dump_html_vocabulary.py"


def _dump_html_vocabulary() -> ModuleType:
    spec = importlib.util.spec_from_file_location("dump_html_vocabulary", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_committed_js_vocabulary_fixture_is_a_fresh_dump() -> None:
    script = _dump_html_vocabulary()
    assert script.FIXTURE.read_text(encoding="utf-8") == script.render(), (
        "js/test/fixtures/html-vocabulary.json is stale: "
        "run `uv run python scripts/dump_html_vocabulary.py`"
    )


def test_the_dump_carries_every_built_in_tag_attribute_and_style() -> None:
    # A dump that read nothing would compare equal to a fixture that holds
    # nothing, so pin it to the table it is built from.
    dumped = json.loads(_dump_html_vocabulary().render())
    assert dumped["extensions"] == sorted(EXTENSION_HTML_VOCABULARY)
    for vocabulary in EXTENSION_HTML_VOCABULARY.values():
        for tag, entry in vocabulary.items():
            assert set(entry.get("attrs", ())) <= set(dumped["tags"][tag]["attributes"])
            assert set(entry.get("styles", ())) <= set(dumped["tags"][tag]["styles"])


def test_the_check_flag_reports_a_stale_fixture(tmp_path: Path) -> None:
    script = _dump_html_vocabulary()
    script.FIXTURE = tmp_path / "html-vocabulary.json"
    script.FIXTURE.write_text("{}\n", encoding="utf-8")
    assert script.main(["--check"]) == 1
    assert script.main([]) == 0
    assert script.main(["--check"]) == 0
