"""Compare the exact JS pins in js/package.json against what npm serves today.

The sibling packages let their manifests declare ranges and close the resulting
gap with a scheduled job that resolves the newest versions the range admits and
runs the suite. js/package.json declares no ranges: every dependency is an exact
version, because the bundles committed under
django_tiptap_editor/static/django_tiptap_editor/ are built from them and the
fidelity corpus is validated against that exact build. A resolve-what-the-
manifest-allows job would therefore resolve straight back to the pins and report
green forever, which is worse than no job at all.

This is the check that replaces it. It asks the registry what exists rather than
what a range admits, so a pin that has fallen behind is visible even though
nothing in the repo can move on its own. It also re-checks the two places that
restate the TipTap pin by hand, because a mirror that disagrees with the pin is
the same failure arriving from the inside.

Exit codes are the interface the workflow reads:

    0  every pin is the newest usable release, and the mirrors agree
    1  drift: a newer release exists, or a mirror disagrees
    2  the check itself could not run (network, bad JSON, missing file)

Two is deliberately distinct from one. Drift is news, not a fault, and a job
that goes red because upstream published a patch teaches its reader to ignore
it. A check that could not reach the registry has learned nothing, and that is
a fault worth a red run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REGISTRY = "https://registry.npmjs.org"

# Abbreviated metadata. It carries dist-tags, the version list and the
# deprecation notices, and is a fraction of the size of the full packument --
# @tiptap/core alone has over five hundred published versions.
ACCEPT = "application/vnd.npm.install-v1+json"

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_JSON = REPO_ROOT / "js" / "package.json"

# The two hand-written restatements of the TipTap pin. The third restatement --
# the version baked into the committed bundles -- is deliberately absent: the
# js-build job in tests.yml rebuilds and diffs those artifacts on every push, so
# a bundle that disagrees with package.json already fails a required check.
MIRRORS: tuple[tuple[Path, str], ...] = (
    (
        REPO_ROOT / "django_tiptap_editor" / "constants.py",
        r'^TIPTAP_VERSION\s*=\s*"([^"]+)"',
    ),
    (
        REPO_ROOT / "js" / "vitest.config.ts",
        r"""__DTT_TIPTAP_VERSION__:\s*'"([^"]+)"'""",
    ),
)

# The package whose version the mirrors restate.
MIRRORED_PIN = "@tiptap/core"

EXIT_CLEAN = 0
EXIT_DRIFTED = 1
EXIT_BROKEN = 2

# Stable releases only. A pin is what consumers install, so a prerelease is not
# a candidate to move to and must not be reported as one.
STABLE_VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")

EXACT_PIN = re.compile(r"^\d+\.\d+\.\d+$")


class CheckFailed(Exception):
    """The check could not be carried out. Distinct from having found drift."""


def read_pins() -> tuple[dict[str, str], list[tuple[str, str]]]:
    """Return the exact pins, plus any specifier that is not an exact pin."""
    try:
        manifest = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CheckFailed(f"could not read {PACKAGE_JSON.name}: {exc}") from exc

    pins: dict[str, str] = {}
    ranges: list[tuple[str, str]] = []
    for section in ("dependencies", "devDependencies"):
        for name, spec in sorted(manifest.get(section, {}).items()):
            if EXACT_PIN.match(spec):
                pins[name] = spec
            else:
                ranges.append((name, spec))
    if not pins and not ranges:
        raise CheckFailed(f"{PACKAGE_JSON.name} declares no dependencies")
    return pins, ranges


def fetch_versions(name: str) -> list[str]:
    """Every non-deprecated stable version the registry currently serves."""
    url = f"{REGISTRY}/{name.replace('/', '%2f')}"
    request = urllib.request.Request(
        url,
        headers={"Accept": ACCEPT, "User-Agent": "django-tiptap-editor-pin-check"},
    )
    last: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                document = json.loads(response.read())
            break
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            last = exc
            # A registry blip must not be reported as a pin having drifted, so
            # retry rather than let one bad response decide the run.
            time.sleep(2 * (attempt + 1))
    else:
        raise CheckFailed(f"{name}: registry unreachable after 3 attempts ({last})")

    versions = document.get("versions", {})
    if not versions:
        raise CheckFailed(f"{name}: registry returned no versions")
    # A deprecated release is not somewhere to move a pin to. Skipping them is
    # not cosmetic here: several @tiptap/* packages published a 3.0.0 they then
    # deprecated as a mistake, and reporting that as the newest major would send
    # the reader after a migration that upstream had already withdrawn.
    return [
        version
        for version, metadata in versions.items()
        if STABLE_VERSION.match(version) and not metadata.get("deprecated")
    ]


def sort_key(version: str) -> tuple[int, int, int]:
    matched = STABLE_VERSION.match(version)
    if matched is None:
        raise CheckFailed(f"unparseable version: {version}")
    return (int(matched[1]), int(matched[2]), int(matched[3]))


def line_of(version: str) -> tuple[int, ...]:
    """The release line a version belongs to, as a caret on it would read it.

    Below 1.0.0 npm's caret stops at the next minor rather than the next major,
    because a 0.x minor is where that ecosystem puts its breaking changes. The
    js-line-latest job relaxes the pins with a caret, so this has to agree with
    it: an esbuild 0.29.0 is a different line from a pinned 0.28.1, and saying
    otherwise would have this check recommend a bump that job never tested.
    """
    major, minor, _ = sort_key(version)
    return (0, minor) if major == 0 else (major,)


def newest(versions: list[str], line: tuple[int, ...] | None = None) -> str | None:
    """The highest stable version, optionally restricted to one release line."""
    candidates = versions if line is None else [v for v in versions if line_of(v) == line]
    return max(candidates, key=sort_key) if candidates else None


def read_mirrors() -> list[tuple[str, str | None]]:
    found: list[tuple[str, str | None]] = []
    for path, pattern in MIRRORS:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise CheckFailed(f"could not read {path.name}: {exc}") from exc
        matched = re.search(pattern, text, re.MULTILINE)
        # None rather than an exception: the constant having been renamed or
        # removed is exactly the kind of silent divergence this check exists to
        # surface, and it should be reported, not crash the run.
        found.append((str(path.relative_to(REPO_ROOT)), matched[1] if matched else None))
    return found


def render(
    pins: dict[str, str],
    latest: dict[str, tuple[str | None, str | None]],
    ranges: list[tuple[str, str]],
    mirrors: list[tuple[str, str | None]],
) -> tuple[str, bool]:
    """Render the report. Returns the markdown and whether anything drifted."""
    in_line: list[str] = []
    beyond_line: list[str] = []
    for name, pinned in sorted(pins.items()):
        line_latest, overall = latest[name]
        if line_latest is not None and sort_key(line_latest) > sort_key(pinned):
            in_line.append(f"| `{name}` | {pinned} | **{line_latest}** |")
        if overall is not None and line_of(overall) != line_of(pinned):
            beyond_line.append(f"| `{name}` | {pinned} | **{overall}** |")

    mirror_rows = [
        f"| `{path}` | {value if value else 'not found'} |"
        for path, value in mirrors
        if value != pins.get(MIRRORED_PIN)
    ]

    sections: list[str] = []
    if mirror_rows:
        sections += [
            "### The TipTap pin is restated somewhere that disagrees",
            "",
            f"`js/package.json` pins `{MIRRORED_PIN}` at "
            f"`{pins.get(MIRRORED_PIN, 'nothing')}`, and these do not say the same:",
            "",
            "| file | says |",
            "| --- | --- |",
            *mirror_rows,
            "",
            "The import map served in external asset mode is built from the value in",
            "`constants.py`, so a disagreement here hands consumers a different TipTap",
            "than the bundle was validated against.",
            "",
        ]
    if in_line:
        sections += [
            "### A newer release inside the pinned line",
            "",
            "| package | pinned | newest in line |",
            "| --- | --- | --- |",
            *in_line,
            "",
            "This is a bump, not a migration. The `js-line-latest` job in the same run",
            "has already built and tested against these versions, so its result says",
            "whether the bump is safe before anyone makes it.",
            "",
        ]
    if beyond_line:
        sections += [
            "### A newer line exists beyond the pinned one",
            "",
            "| package | pinned | newest overall |",
            "| --- | --- | --- |",
            *beyond_line,
            "",
            "This is a migration decision rather than a bump, so nothing in CI can",
            "make it and `js-line-latest` deliberately does not test it. It is listed",
            "so the gap is a decision on the record instead of something nobody has",
            "looked at in a year.",
            "",
        ]
    if ranges:
        sections += [
            "### Not compared (not an exact pin)",
            "",
            "| package | specifier |",
            "| --- | --- |",
            *[f"| `{name}` | `{spec}` |" for name, spec in ranges],
            "",
            "This check compares pins. Anything declared as a range needs the other",
            "shape of drift job -- resolve what the range admits, then run the suite.",
            "",
        ]

    drifted = bool(mirror_rows or in_line or beyond_line)
    if not drifted:
        return ("", False)

    fingerprint = hashlib.sha256(
        "\n".join(mirror_rows + in_line + beyond_line).encode("utf-8")
    ).hexdigest()[:12]
    body = [
        "The weekly pin check found the committed JavaScript pins behind what the",
        "registry serves, or restated inconsistently inside the repo.",
        "",
        *sections,
        "The pins are exact on purpose: the committed bundles are built from them and",
        "the fidelity corpus is validated against that build. Moving one means running",
        "`make build-js` and committing the rebuilt bundles in the same change.",
        "",
        f"<!-- js-pin-drift: {fingerprint} -->",
    ]
    return ("\n".join(body), True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--report",
        type=Path,
        help="write the issue body here when something drifted (nothing is written otherwise)",
    )
    arguments = parser.parse_args()

    try:
        pins, ranges = read_pins()
        mirrors = read_mirrors()
        latest: dict[str, tuple[str | None, str | None]] = {}
        for name, pinned in sorted(pins.items()):
            versions = fetch_versions(name)
            line_latest = newest(versions, line=line_of(pinned))
            overall = newest(versions)
            latest[name] = (line_latest, overall)
            # Always printed, drift or not: a green run that names every version
            # it looked at is auditable, and a run that only speaks up when it
            # is unhappy is indistinguishable from one that did nothing.
            print(f"{name:<40} pinned {pinned:<10} line {line_latest or '-':<10} newest {overall}")
        for path, value in mirrors:
            print(f"{path:<40} says {value or 'nothing'}")
    except CheckFailed as exc:
        print(f"pin check could not run: {exc}", file=sys.stderr)
        return EXIT_BROKEN

    body, drifted = render(pins, latest, ranges, mirrors)
    if not drifted:
        print("\nNo drift: every pin is the newest usable release and the mirrors agree.")
        return EXIT_CLEAN

    print("\n" + body)
    if arguments.report:
        arguments.report.write_text(body + "\n", encoding="utf-8")
    return EXIT_DRIFTED


if __name__ == "__main__":
    raise SystemExit(main())
