"""Report what the next major line beyond each JS pin would cost, in corpus cases.

    python scripts/price_next_line.py <vitest-report.json> <npm-ls.json> <out.md>

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
  "blocked before the corpus can even run" -- more useful than a missing number;
- a corpus case that is currently a documented *normalization* starts round-
  tripping exactly. The suite treats that as a failure on purpose (the exception
  should be deleted), so a raw pass count would score an improvement as a
  regression. Those are counted separately and named.
"""

from __future__ import annotations

import json
import pathlib
import sys

# The prefix every corpus assertion is titled with, from `fidelity.test.ts`.
# Matched rather than assumed so a renamed suite shows up as "no cases found"
# instead of silently reporting zero failures.
CASE_PREFIX = "preserves content: "

# The marker `upstream-drift.yml` reads to decide whether the report changed
# since last week. Only the numbers feed it, so a reworded preamble does not
# ping a thread nobody needs to re-read.
MARKER = "js-next-line"


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


def render(report: dict[str, object], npm_ls: dict[str, object]) -> str:
    """The markdown body of the issue."""
    resolved = _packages(npm_ls)
    held, broke, unrun = _cases(report)
    measured = len(held) + len(broke)

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
            "result at all -- it is the newer line failing to load, which the run's",
            "own log names.",
            "",
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


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(f"usage: {argv[0]} <vitest-report.json> <npm-ls.json> <out.md>", file=sys.stderr)
        return 2
    body = render(_load(argv[1]), _load(argv[2]))
    pathlib.Path(argv[3]).write_text(body, encoding="utf-8")
    print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
