"""Every hand-written restatement of the TipTap pin agrees with js/package.json.

scripts/check_js_pins.py already compares them, but only inside the scheduled
upstream-drift workflow, which never runs on a pull request. So a release that
moved the pin and missed a restatement could merge green and be reported a day
later, after it had published. Meanwhile the per-PR test of the import map,
``test_get_import_map``, builds its expected URL from ``TIPTAP_VERSION`` itself
and so can only ever agree with it.

The mirror half of the script needs no network, so it runs here on every pull
request. It is loaded from the script rather than restated, so the list of
places it checks stays one list.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check_js_pins.py"


def _check_js_pins() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_js_pins", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_restatement_of_the_tiptap_pin_agrees_with_package_json() -> None:
    script = _check_js_pins()
    pins, _ = script.read_pins()
    mirrors = script.read_mirrors()

    # Without this the comparison below passes by reading nothing, should the
    # list be emptied or a file stop matching its pattern (which reads as None,
    # not as an exception, by design).
    assert {path for path, _ in mirrors} == {
        "django_tiptap_editor/constants.py",
        "js/vitest.config.ts",
        "docs/asset-modes.md",
    }

    assert dict(mirrors) == dict.fromkeys(dict(mirrors), pins[script.MIRRORED_PIN])
