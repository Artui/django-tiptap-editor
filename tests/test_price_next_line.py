"""The weekly next-major report says what blocked it, and stops once there is no next major.

scripts/price_next_line.py runs only inside the scheduled upstream-drift
workflow, so nothing on a pull request ever exercised it, and two of its answers
had gone wrong without anything failing:

- When the newer line failed to load, the report said "the run's own log names"
  the error. The workflow ran vitest with the JSON reporter alone, which records
  a suite whose setup threw as 48 skipped cases and an empty message, so the log
  never had it. The issue priced the migration as blocked and could not say by
  what.
- Once the pins cross a major, ``latest`` is the pinned line again, and the job
  would go on reporting a corpus run under a heading about crossing a major.

The files under ``fixtures/next_line`` come from the producers rather than from
memory: vitest 4.1.11's default and JSON reporters, and npm 11's
``npm ls --depth 0 --json``, all run against Tiptap 3.31.4 installed over the
committed 2.x manifest the way the job installs it.

- ``blocked.txt`` and ``blocked.json`` are one run, uncoloured.
- ``blocked-ci.txt`` is the same run under ``CI=true GITHUB_ACTIONS=true`` in an
  otherwise empty environment, which is what turns vitest's colours on; it
  turns them off when it detects a coding agent, which is why the first
  capture is plain.
- ``startup-error-ci.txt`` is the same command pointed at a config that throws,
  so vitest dies before collecting anything and writes no JSON.

The only edits are that absolute paths were cut back to repo-relative ones, or
to ``<repo>`` and ``<scratch>`` where the path was outside the repository, and
that the end-of-file hook trimmed the blank lines vitest printed last. The
reporter output is ``.txt`` rather than ``.log`` because the repository ignores
``*.log``.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

_REPO = Path(__file__).resolve().parent.parent
_SCRIPT = _REPO / "scripts" / "price_next_line.py"
_WORKFLOW = _REPO / ".github" / "workflows" / "upstream-drift.yml"
_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "next_line"

# The committed manifest at the time the fixtures were captured. Stated here
# rather than read from js/package.json, so these cases do not change meaning
# the day the pins cross a major.
_PINNED_2X = {"dependencies": {"@tiptap/core": "2.27.3"}}
_PINNED_3X = {"dependencies": {"@tiptap/core": "3.31.4"}}


def _script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("price_next_line", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _json(name: str) -> Any:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


def _text(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def _log() -> str:
    return _text("blocked.txt")


def _quoted(body: str) -> str:
    """The fenced block the report quotes, without its fences."""
    return body.split("\n\n```\n", 1)[1].split("\n```\n", 1)[0]


def _passing_report() -> Any:
    """The blocked run's report as it reads once every case runs and holds."""
    report = _json("blocked.json")
    for suite in report["testResults"]:
        suite["status"] = "passed"
        for case in suite["assertionResults"]:
            case["status"] = "passed"
    return report


def test_the_json_report_alone_does_not_name_what_blocked_the_suite() -> None:
    # The premise of the fix, checked against the producer's own output: every
    # case skipped, the suite failed with an empty message, and nowhere in the
    # document the error the default reporter prints.
    report = _json("blocked.json")
    (suite,) = report["testResults"]
    assert suite["status"] == "failed"
    assert suite["message"] == ""
    assert {case["status"] for case in suite["assertionResults"]} == {"skipped"}
    assert "configure" not in (_FIXTURES / "blocked.json").read_text(encoding="utf-8")
    assert "reading 'configure'" in _log()


def test_a_blocked_run_quotes_the_error_that_blocked_it() -> None:
    body = _script().render(_json("blocked.json"), _log(), _json("npm-ls.json"), _PINNED_2X)

    assert "## Blocked before anything could be measured" in body
    assert "What stopped it, from vitest's 'Failed Suites 1' section:" in body
    quoted = _quoted(body)
    # Quoted as printed, indentation included, since the code frame below it
    # lines up a caret under the failing column.
    assert quoted.splitlines()[0] == " FAIL  test/fidelity.test.ts > fidelity corpus round-trip"
    assert "TypeError: Cannot read properties of undefined (reading 'configure')" in quoted
    # The frame in our own code is what makes the report actionable without
    # opening the run; the divider that closes the section is not quoted.
    assert "src/build-extensions.ts:102:11" in quoted
    assert quoted.endswith(" \u276f test/fidelity.test.ts:39:19")
    assert "\u23af" not in quoted
    assert "own log names" not in body
    assert "<!-- js-next-line: " in body


def test_the_error_is_found_through_the_colours_ci_turns_on() -> None:
    # On a runner vitest colours the dividers themselves as well as the titles,
    # so both the section header and the divider that ends it start with an
    # escape rather than with U+23AF.
    coloured = _text("blocked-ci.txt")
    assert "\x1b[31m\u23af" in coloured
    assert "\x1b[31m\x1b[2m\u23af" in coloured

    script = _script()
    assert script._error_section(coloured) == script._error_section(_log())
    assert script.render(
        _json("blocked.json"), coloured, _json("npm-ls.json"), _PINNED_2X
    ) == script.render(_json("blocked.json"), _log(), _json("npm-ls.json"), _PINNED_2X)


def test_a_vitest_that_cannot_start_quotes_its_startup_error() -> None:
    # No JSON is written at all in this case, so the report reads none.
    body = _script().render({}, _text("startup-error-ci.txt"), _json("npm-ls.json"), _PINNED_2X)

    assert "## Blocked before anything could be measured" in body
    assert "What stopped it, from vitest's 'Startup Error' section:" in body
    quoted = _quoted(body)
    # The section runs to the end of the output rather than to a closing
    # divider, and the line before it is not part of it.
    assert quoted.splitlines()[0] == "Error: config-broke-here"
    assert "loadConfigFromFile" in quoted
    assert "failed to load config" not in quoted


def test_output_with_no_error_section_is_quoted_from_its_end() -> None:
    script = _script()
    log = "\n".join(["", *(f"line {n}" for n in range(40)), "sh: 1: vitest: not found", "", ""])
    body = script.render({}, log, _json("npm-ls.json"), _PINNED_2X)

    assert "Vitest printed no error section. Its output ended:" in body
    quoted = _quoted(body).splitlines()
    assert len(quoted) == script._ERROR_LINES
    assert quoted[-1] == "sh: 1: vitest: not found"


def test_a_vitest_step_with_no_output_says_there_is_nothing_to_quote() -> None:
    body = _script().render(_json("blocked.json"), "", _json("npm-ls.json"), _PINNED_2X)

    assert "## Blocked before anything could be measured" in body
    assert "```" not in body
    assert "left no output" in body
    # The install step cannot be where it is: a failed install stops the job
    # before the report is written.
    assert "install" not in body


def test_the_quoted_error_is_capped() -> None:
    script = _script()
    divider = "\u23af" * 6
    log = "\n".join(
        [f"{divider} Failed Suites 1 {divider}", "", *(f"frame {n}" for n in range(100))]
    )
    assert script._error_section(log) == (
        "Failed Suites 1",
        [f"frame {n}" for n in range(script._ERROR_LINES)],
    )


def test_a_closing_divider_is_not_taken_for_a_section() -> None:
    # It carries a counter, "[1/1]", with no spaces around it; read as a
    # header, the output's ending would be quoted under the title "[1/1]".
    script = _script()
    log = "\n".join(["before", "\u23af" * 20 + "[1/1]" + "\u23af", "after"])
    assert script._error_section(log) == ("", ["before", "\u23af" * 20 + "[1/1]\u23af", "after"])


@pytest.mark.parametrize("pinned_core", ["3.31.4", "3.0.0", "^3.31.4", "~3.31.4", "4.0.0"])
def test_no_newer_major_is_reported_as_such_and_not_priced(pinned_core: str) -> None:
    # 4.0.0 is the pins having moved past what `latest` resolved, which the
    # registry should never produce but which is still not a major to price.
    script = _script()
    pinned = {"dependencies": {"@tiptap/core": pinned_core}}
    body = script.render(_json("blocked.json"), _log(), _json("npm-ls.json"), pinned)

    assert body.startswith("## No newer Tiptap major has been published\n")
    assert "3.31.4" in body
    assert script.NOTHING_TO_PRICE in body
    assert "Blocked" not in body
    assert "round-trip" not in body
    # The fingerprint is what the workflow compares to decide whether to
    # comment; a closing report carries none, so it can never be mistaken for
    # an unchanged price.
    assert "<!-- js-next-line: " not in body


@pytest.mark.parametrize(
    "pinned",
    [
        _PINNED_2X,
        {"dependencies": {"@tiptap/core": "~2.27.3"}},
        # A manifest the step failed to save, or one that no longer names the
        # core package, keeps reporting rather than closing the issue on a
        # guess.
        {},
        {"dependencies": {}},
        {"dependencies": {"@tiptap/core": "latest"}},
        {"dependencies": ["@tiptap/core"]},
        {"dependencies": {"@tiptap/core": 3}},
    ],
)
def test_a_newer_major_is_still_priced(pinned: dict[str, object]) -> None:
    script = _script()
    body = script.render(_json("blocked.json"), _log(), _json("npm-ls.json"), pinned)

    assert script.NOTHING_TO_PRICE not in body
    assert "## Blocked before anything could be measured" in body


def test_a_corpus_that_holds_on_the_pinned_line_is_not_priced() -> None:
    # The case the check exists for. Once the pins cross, `latest` is the line
    # already pinned and the corpus passes on it, which without the check
    # reads "48 of 48 documents still round-trip" under a heading about
    # crossing a major.
    script = _script()
    body = script.render(_passing_report(), "", _json("npm-ls.json"), _PINNED_3X)

    assert script.NOTHING_TO_PRICE in body
    assert "round-trip" not in body
    # And the same report under a 2.x pin is priced, so the fixture is one the
    # pricing branch accepts.
    priced = script.render(_passing_report(), "", _json("npm-ls.json"), _PINNED_2X)
    assert "## 48 of 48 documents still round-trip" in priced


def test_an_unresolved_core_is_priced_rather_than_closed() -> None:
    script = _script()
    npm_ls = {"dependencies": {"@tiptap/core": {}}}
    body = script.render(_json("blocked.json"), _log(), npm_ls, _PINNED_3X)

    assert script.NOTHING_TO_PRICE not in body
    assert "| `@tiptap/core` | (unresolved) |" in body


def test_the_workflow_closes_on_the_marker_the_script_writes() -> None:
    # The two halves agree on one literal string across a language boundary,
    # and a mismatch fails silently: the issue would be updated with "no newer
    # major" every week instead of closed.
    assert _script().NOTHING_TO_PRICE in _WORKFLOW.read_text(encoding="utf-8")


def test_main_writes_the_report_from_the_five_files_the_workflow_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pinned = tmp_path / "package.pinned.json"
    pinned.write_text(json.dumps(_PINNED_2X), encoding="utf-8")
    out = tmp_path / "js-next-line.md"
    argv = [
        str(_SCRIPT),
        str(_FIXTURES / "blocked.json"),
        str(_FIXTURES / "blocked.txt"),
        str(_FIXTURES / "npm-ls.json"),
        str(pinned),
        str(out),
    ]

    assert _script().main(argv) == 0
    assert "reading 'configure'" in out.read_text(encoding="utf-8")
    assert "reading 'configure'" in capsys.readouterr().out


def test_main_survives_a_log_the_step_never_wrote(tmp_path: Path) -> None:
    out = tmp_path / "js-next-line.md"
    argv = [
        str(_SCRIPT),
        str(tmp_path / "missing.json"),
        str(tmp_path / "missing.log"),
        str(tmp_path / "missing-ls.json"),
        str(tmp_path / "missing-package.json"),
        str(out),
    ]

    assert _script().main(argv) == 0
    assert "left no output" in out.read_text(encoding="utf-8")


def test_main_refuses_the_old_three_file_call(capsys: pytest.CaptureFixture[str]) -> None:
    assert _script().main(["price_next_line.py", "a.json", "b.json", "out.md"]) == 2
    assert "<vitest.log>" in capsys.readouterr().err
