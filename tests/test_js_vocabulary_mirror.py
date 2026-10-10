"""The JS tests read the current HTML vocabulary and feature model, not stale copies.

js/test/html-vocabulary.test.ts checks that everything the editor can emit is
something EXTENSION_HTML_VOCABULARY keeps. It reads the vocabulary from a JSON
fixture, because the JS suite cannot import Python. That check is only as good
as the fixture is current, so this compares the committed file with a fresh
dump on every pull request. The feature model (FEATURE_CORE and
FEATURE_DEPENDENCIES) reaches the JS suite the same way, as
js/test/fixtures/feature-model.json, and is checked the same way. The dump is
loaded from the script rather than restated, so there is one definition of each
fixture's shape.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

from django_tiptap_editor.constants import (
    BUILTIN_EXTENSIONS,
    DECORATING_FEATURES,
    DOCUMENT_FEATURES,
    EXTENSION_HTML_VOCABULARY,
    FEATURE_CORE,
    FEATURE_DEPENDENCIES,
)

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
    for name, vocabulary in EXTENSION_HTML_VOCABULARY.items():
        # The per-extension copy is the table itself, not a union, because the
        # JS suite checks each feature's editor against its own entry.
        assert set(dumped["byExtension"][name]) == set(vocabulary)
        for tag, entry in vocabulary.items():
            assert set(entry.get("attrs", ())) <= set(dumped["tags"][tag]["attributes"])
            assert set(entry.get("styles", ())) <= set(dumped["tags"][tag]["styles"])
            assert dumped["byExtension"][name][tag] == {
                "attributes": sorted(entry.get("attrs", ())),
                "styles": sorted(entry.get("styles", ())),
            }
    assert dumped["decorating"] == sorted(DECORATING_FEATURES)
    assert dumped["documentFeatures"] == DOCUMENT_FEATURES


def test_the_committed_js_feature_model_fixture_is_a_fresh_dump() -> None:
    script = _dump_html_vocabulary()
    assert script.FEATURES_FIXTURE.read_text(encoding="utf-8") == script.render_features(), (
        "js/test/fixtures/feature-model.json is stale: "
        "run `uv run python scripts/dump_html_vocabulary.py`"
    )


def test_the_feature_model_dump_carries_the_core_and_every_dependency() -> None:
    # As above: a dump of nothing would match a fixture of nothing.
    dumped = json.loads(_dump_html_vocabulary().render_features())
    assert dumped["core"] == sorted(FEATURE_CORE)
    assert dumped["features"] == sorted(BUILTIN_EXTENSIONS - FEATURE_CORE)
    assert dumped["dependencies"] == {
        name: sorted(deps) for name, deps in FEATURE_DEPENDENCIES.items()
    }


def _redirected(tmp_path: Path) -> ModuleType:
    """Load the script with both fixture paths pointed into ``tmp_path``.

    ``main([])`` writes both files, so a test that redirected only one would
    rewrite the committed copy of the other on every run, and the freshness test
    above would then pass whatever the committed file held.
    """
    script = _dump_html_vocabulary()
    script.FIXTURE = tmp_path / "html-vocabulary.json"
    script.FEATURES_FIXTURE = tmp_path / "feature-model.json"
    return script


def test_the_check_flag_reports_a_stale_vocabulary_fixture(tmp_path: Path) -> None:
    script = _redirected(tmp_path)
    script.FIXTURE.write_text("{}\n", encoding="utf-8")
    script.FEATURES_FIXTURE.write_text(script.render_features(), encoding="utf-8")
    assert script.main(["--check"]) == 1
    assert script.main([]) == 0
    assert script.main(["--check"]) == 0


def test_the_check_flag_reports_a_stale_feature_model_fixture(tmp_path: Path) -> None:
    # The vocabulary fixture is fresh here, so only the feature-model half of
    # the check can be the one answering.
    script = _redirected(tmp_path)
    script.FIXTURE.write_text(script.render(), encoding="utf-8")
    script.FEATURES_FIXTURE.write_text("{}\n", encoding="utf-8")
    assert script.main(["--check"]) == 1
    assert script.main([]) == 0
    assert script.FEATURES_FIXTURE.read_text(encoding="utf-8") == script.render_features()
    assert script.main(["--check"]) == 0
