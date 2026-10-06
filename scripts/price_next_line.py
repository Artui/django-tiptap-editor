"""Report what the next major line beyond each JS pin would cost, in corpus cases.

    python scripts/price_next_line.py <vitest-report.json> <vitest.log> <npm-ls.json> \
        <pinned-package.json> <out.md>

`check_js_pins.py` already says a newer *line* exists -- Tiptap 3.x beyond a
pinned 2.x, and so on -- and stops there, correctly: whether to cross a major is
a migration decision no check can make. What it cannot say is what crossing
would **cost**, and that is the number this writes down.

The cost is measured in the only currency this package has for schema changes:
the fidelity corpus. Forty-eight real-world documents through the production
extension set, each its own test, each either preserving its content or not. A
run against the newest line turns "a migration nobody has looked at in a year"
into "41 of 48 still round-trip, and here are the seven that do not" -- which is
a scope rather than a fear, and it moves on its own as upstream fixes things.

**This never fails a build and never proposes a bump.** It reports. The pins in
`js/package.json` have not moved and nothing shipped is affected; what the report
buys is that the decision is repriced weekly instead of aging quietly.

Two failure modes are reported rather than hidden, because both are answers:

- the install or the type-check falls over, which prices the migration as
  "blocked before the corpus can even run" -- more useful than a missing number,
  and only useful at all if the report quotes what fell over (see
  ``_error_section``);
- a corpus case that is currently a documented *normalization* starts round-
  tripping exactly. The suite treats that as a failure on purpose (the exception
  should be deleted), so a raw pass count would score an improvement as a
  regression. Those are counted separately and named.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

# The prefix every corpus assertion is titled with, from `fidelity.test.ts`.
# Matched rather than assumed so a renamed suite shows up as "no cases found"
# instead of silently reporting zero failures.
CASE_PREFIX = "preserves content: "

# The marker `upstream-drift.yml` reads to decide whether the report changed
# since last week. Only the numbers feed it, so a reworded preamble does not
# ping a thread nobody needs to re-read.
MARKER = "js-next-line"

# The second marker the workflow reads. When the newest Tiptap is inside the
# pinned major there is nothing to price, and the workflow closes the issue
# rather than keep a standing "what the next major would cost" with no answer.
NOTHING_TO_PRICE = f"<!-- {MARKER}-status: no-newer-major -->"

# Vitest's default reporter colours its output on a CI runner, and the divider
# it draws around each error section is a run of U+23AF. Both are named by
# escape rather than pasted, so the pattern survives an editor or a hook that
# normalises either.
_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_DIVIDER = "\u23af"

# A section is opened by a divider with a title in it -- "Failed Suites 1",
# "Startup Error", "Unhandled Errors". The divider that closes one carries a
# counter with no spaces around it ("[1/1]"), which this does not match.
_SECTION = re.compile(rf"^{_DIVIDER}+ (.+?) {_DIVIDER}+$")

# Enough of a stack to name the file and line in our code, which is all the
# report needs; the run's own log has the rest.
_ERROR_LINES = 24


def _packages(npm_ls: dict[str, object]) -> dict[str, str]:
    """Every top-level dependency and the version this run resolved for it."""
    dependencies = npm_ls.get("dependencies")
    if not isinstance(dependencies, dict):
        return {}
    resolved: dict[str, str] = {}
    for name, entry in sorted(dependencies.items()):
        version = entry.get("version") if isinstance(entry, dict) else None
        resolved[name] = str(version) if version else "(unresolved)"
    return resolved


def _cases(report: dict[str, object]) -> tuple[list[str], list[str], list[str]]:
    """The corpus cases that held, that did not, and that never ran.

    Read out of the per-assertion results rather than the suite totals, because
    the totals count the whole file: one unrelated test in the same run would
    move a number that is supposed to mean "documents that survived".

    **The third list is the one that matters most, and it was found the hard
    way.** The suite builds one editor in ``beforeAll``; if that throws -- which
    is exactly what a breaking upstream change does first -- vitest marks every
    case *skipped*, not failed. Counting "not passed" as "did not hold" scored
    that as 48 documents losing content, when the truth was that none had been
    measured. A wrong number is worse than a missing one here, because the whole
    job exists to be believed without re-running it.
    """
    held: list[str] = []
    broke: list[str] = []
    unrun: list[str] = []
    suites = report.get("testResults")
    for suite in suites if isinstance(suites, list) else []:
        assertions = suite.get("assertionResults") if isinstance(suite, dict) else None
        for assertion in assertions if isinstance(assertions, list) else []:
            title = str(assertion.get("title", ""))
            if not title.startswith(CASE_PREFIX):
                continue
            case = title[len(CASE_PREFIX) :]
            status = assertion.get("status")
            if status == "passed":
                held.append(case)
            elif status == "failed":
                broke.append(case)
            else:
                unrun.append(case)
    return held, broke, unrun


def _trim(lines: list[str]) -> list[str]:
    """``lines`` without the blank lines at either end."""
    start, end = 0, len(lines)
    while start < end and not lines[start]:
        start += 1
    while end > start and not lines[end - 1]:
        end -= 1
    return lines[start:end]


def _error_section(log: str) -> tuple[str, list[str]]:
    """The first error section vitest's default reporter printed, and its title.

    **This exists because the JSON report does not carry it.** When the suite's
    ``beforeAll`` throws -- the front door a breaking major falls over first --
    vitest's JSON reporter records every case as skipped, the suite as failed,
    and the suite's ``message`` as an empty string. The error itself is printed
    only by the default reporter, under a "Failed Suites" divider. Before this
    read it, the issue said the run's log named the error while the workflow
    ran the JSON reporter alone, so the report priced the migration as blocked
    and nobody could see by what.

    Any titled section is taken, not only that one: a vitest that cannot load
    its config prints a "Startup Error" section instead, which runs to the end
    of the output rather than to a closing divider, and writes no JSON at all.
    With no section, the title is empty and the lines are the last ones the
    output had, since whatever ended it is the nearest thing to a cause.
    """
    lines = _ANSI.sub("", log).splitlines()
    for index, line in enumerate(lines):
        header = _SECTION.match(line)
        if header is None:
            continue
        block: list[str] = []
        for body in lines[index + 1 :]:
            if body.startswith(_DIVIDER):
                break
            block.append(body)
        return header[1], _trim(block)[:_ERROR_LINES]
    return "", _trim(lines)[-_ERROR_LINES:]


def _major(version: str | None) -> int | None:
    """The leading number of a version or exact pin, or None if there is none."""
    matched = re.match(r"\s*[\^~]?(\d+)\.", version or "")
    return int(matched[1]) if matched else None


def _no_newer_major(resolved: dict[str, str], pinned: dict[str, object]) -> bool:
    """Whether the newest Tiptap this run resolved is inside the pinned major.

    The job sets every Tiptap package to ``latest``, which is the next major
    only while one exists. Once the pins have crossed it, ``latest`` is the
    pinned line again, and a corpus run against it would be reported as "every
    case held" under a heading about crossing a major -- a true number
    answering a question nobody asked.
    """
    dependencies = pinned.get("dependencies")
    pin = dependencies.get("@tiptap/core") if isinstance(dependencies, dict) else None
    pinned_major = _major(pin if isinstance(pin, str) else None)
    resolved_major = _major(resolved.get("@tiptap/core"))
    if pinned_major is None or resolved_major is None:
        return False
    return resolved_major <= pinned_major


def _fingerprint(held: list[str], broke: list[str], resolved: dict[str, str]) -> str:
    """A digest of the answer, so an unchanged answer is not re-announced.

    Deliberately covers the resolved versions as well as the counts: the same
    score against a newer upstream is a different fact, and the point of the
    report is to notice when upstream moves.
    """
    import hashlib

    payload = json.dumps(
        {"held": sorted(held), "broke": sorted(broke), "resolved": resolved},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:12]


def render(
    report: dict[str, object],
    log: str,
    npm_ls: dict[str, object],
    pinned: dict[str, object],
) -> str:
    """The markdown body of the issue."""
    resolved = _packages(npm_ls)
    held, broke, unrun = _cases(report)
    measured = len(held) + len(broke)

    if _no_newer_major(resolved, pinned):
        lines = [
            "## No newer Tiptap major has been published",
            "",
            f"The newest `@tiptap/core` is {resolved['@tiptap/core']}, inside the",
            "major `js/package.json` already pins, so there is no migration to",
            "price. The pinned-line job covers the newest release in that major.",
            "",
            "This closes the issue; the first run that finds a newer major opens",
            "a fresh one.",
            "",
            NOTHING_TO_PRICE,
        ]
        return "\n".join(lines) + "\n"

    lines = [
        "The weekly run against the newest release of every Tiptap package --",
        "crossing the major that the pinned-line job deliberately stops below --",
        "has finished. This is what that migration would cost today.",
        "",
    ]

    if measured == 0:
        lines += [
            "## Blocked before anything could be measured",
            "",
            f"{len(unrun) or 'No'} corpus cases were collected and none of them ran.",
            "The suite builds one editor before the first case; when that throws,",
            "every case is skipped rather than failed. So this is not a fidelity",
            "result at all -- it is the newer line failing to load.",
            "",
        ]
        title, error = _error_section(log)
        if title:
            lines += [f"What stopped it, from vitest's {title!r} section:", ""]
            lines += ["```", *error, "```", ""]
        elif error:
            lines += ["Vitest printed no error section. Its output ended:", ""]
            lines += ["```", *error, "```", ""]
        else:
            lines += [
                "The vitest step left no output, so there is nothing to quote here;",
                "that step in the run above is the place to look.",
                "",
            ]
        lines += [
            "That is still an answer, and a cheap one: it prices the migration as",
            "*blocked at the front door* rather than expensive in the corpus, and",
            "the front door is usually one import or one renamed export.",
            "",
        ]
    else:
        lines += [
            f"## {len(held)} of {measured} documents still round-trip",
            "",
            "Each case is one real-world document through the production extension",
            "set. A case that does not hold has either lost content or stopped",
            "matching the normalization recorded for it -- and the second is an",
            "*improvement* the suite reports as a failure on purpose, so read the",
            "run before reading the count as damage.",
            "",
        ]
        if broke:
            lines += ["Cases that did not hold:", ""]
            lines += [f"- `{case}`" for case in sorted(broke)]
            lines += [
                "",
                "A cluster here usually has one cause rather than one per case --",
                "a default that changed, a node the schema gained. Read two of them",
                "before costing all of them.",
                "",
            ]
        else:
            lines += [
                "**Every case held.** On this evidence the schema survives the",
                "newer line intact, which makes the migration a dependency and",
                "configuration exercise rather than a fidelity one.",
                "",
            ]
        if unrun:
            lines += [
                f"{len(unrun)} case(s) were skipped and are excluded from the count",
                "above, since a case that did not run is not a case that lost.",
                "",
            ]

    if resolved:
        tiptap = {n: v for n, v in resolved.items() if n.startswith("@tiptap/")}
        other = {n: v for n, v in resolved.items() if not n.startswith("@tiptap/")}
        lines += ["## What it resolved to", "", "| package | version |", "| --- | --- |"]
        lines += [f"| `{name}` | {version} |" for name, version in tiptap.items()]
        lines.append("")
        if other:
            # Named explicitly because the toolchain being *held* is what makes the
            # number attributable: an earlier version of this job moved everything
            # at once and a jsdom/Node incompatibility read as a schema failure.
            lines += [
                "Held at their committed pins, so the result above is attributable",
                "to the schema rather than to the test toolchain: "
                + ", ".join(f"`{n}` {v}" for n, v in other.items())
                + ".",
                "",
            ]

    lines += [
        "Nothing here is a proposal. The pins in `js/package.json` have not moved,",
        "`tests.yml` is green, and consumers are unaffected. Crossing a major stays",
        "a decision; this only keeps its price current.",
        "",
        f"<!-- {MARKER}: {_fingerprint(held, broke, resolved)} -->",
    ]
    return "\n".join(lines) + "\n"


def _load(path: str) -> dict[str, object]:
    """Parse a JSON file, or return an empty document if the step never wrote one.

    A missing or malformed file is the "it fell over" case, which `render`
    reports as no cases found rather than crashing -- the report is the whole
    point of the job, so it has to survive the thing it is reporting on.
    """
    try:
        loaded = json.loads(pathlib.Path(path).read_text())
    except (OSError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _read(path: str) -> str:
    """A text file's contents, or empty if the step never wrote it."""
    try:
        return pathlib.Path(path).read_text(encoding="utf-8")
    except OSError:
        return ""


def main(argv: list[str]) -> int:
    if len(argv) != 6:
        print(
            f"usage: {argv[0]} <vitest-report.json> <vitest.log> <npm-ls.json>"
            " <pinned-package.json> <out.md>",
            file=sys.stderr,
        )
        return 2
    body = render(_load(argv[1]), _read(argv[2]), _load(argv[3]), _load(argv[4]))
    pathlib.Path(argv[5]).write_text(body, encoding="utf-8")
    print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
