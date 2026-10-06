"""Every job in upstream-drift.yml that opens an issue also closes it.

The workflow runs only on its weekly schedule, never on a pull request, so a job
that opens an issue and has no way to close it merges green and is found months
later as an issue nobody can tell is current. Three of the four jobs shipped that
way. The opening and the closing step find the issue by exact title, so each job
names it once in ``ISSUE_TITLE``, and two jobs sharing a title would close each
other's issues.

The workflow is read as text rather than parsed: the checks are about which
strings a job's block contains, and PyYAML is not a dependency of this repo.
"""

from __future__ import annotations

import re
from pathlib import Path

_WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "upstream-drift.yml"


def _jobs() -> dict[str, str]:
    """Each job's name mapped to the text of its block."""
    text = _WORKFLOW.read_text(encoding="utf-8")
    body = text.split("\njobs:\n", 1)[1]
    parts = re.split(r"^  ([a-z][a-z0-9-]*):\n", body, flags=re.MULTILINE)
    return dict(zip(parts[1::2], parts[2::2], strict=True))


def _opening_jobs() -> dict[str, str]:
    return {name: block for name, block in _jobs().items() if "issues.create(" in block}


def test_the_jobs_that_open_issues_are_all_found() -> None:
    # Guards the parse: a split that found no jobs would pass every test below.
    assert set(_opening_jobs()) == {
        "resolve-latest",
        "js-line-latest",
        "js-next-line",
        "js-pin-drift",
    }


def test_every_job_that_opens_an_issue_can_close_it() -> None:
    for name, block in _opening_jobs().items():
        assert 'state: "closed"' in block, f"{name} opens an issue and never closes it"


def test_every_job_names_its_issue_once() -> None:
    for name, block in _opening_jobs().items():
        # Job level (four spaces), so every step in the job reads the same value.
        assert len(re.findall(r"^    env:\n      ISSUE_TITLE: ", block, re.MULTILINE)) == 1, name
        assert "process.env.ISSUE_TITLE" in block, name
        assert 'const title = "' not in block, f"{name} restates its title in a script"
        assert 'issue.title === "' not in block, f"{name} restates its title in a script"


def test_no_two_jobs_share_an_issue() -> None:
    titles = []
    for block in _opening_jobs().values():
        match = re.search(r"^      ISSUE_TITLE: (.+)$", block, re.MULTILINE)
        assert match is not None
        titles.append(match.group(1))
    assert len(set(titles)) == len(titles)
