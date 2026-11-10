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

    # Without this the comparison below passes by reading nothing.
    assert {path for path, _ in mirrors} == {
        "django_tiptap_editor/constants.py",
        "js/vitest.config.ts",
        "docs/asset-modes.md",
    }

    assert dict(mirrors) == dict.fromkeys(dict(mirrors), pins[script.MIRRORED_PIN])
