# Repo conventions for `django-tiptap-editor`

This file is the single source of truth for how to write code in this package.
Rules are non-negotiable unless flagged as a heuristic. It matches the shared
standard used by `djangorestframework-services` and `djangorestframework-mcp-server`,
with one deliberate deviation: an **embedded esbuild JS build** (see "JavaScript build").

## What this package is

A reusable Django package providing a drop-in TipTap (headless ProseMirror) rich-text
editor: a form `Widget`, an admin widget, a `ModelAdmin` mixin, a settings default, and
vendored static assets — node-free for consumers. The stored value is **HTML**, never
JSON. The hard engineering problem is the ProseMirror schema/extension set that
round-trips real authored HTML without loss — not the Django plumbing.

The design plan lives in the ecosystem planning repo
(`docs/plans/repos/django-tiptap-editor/plan.md`); the 8-phase tracker there is the
roadmap. This file governs *how* code is written.

## Commands

| Target | What it does |
| --- | --- |
| `make init` | `uv sync --all-groups` + install pre-commit hooks |
| `make test` | `uv run pytest` with coverage (100% line+branch required) |
| `make lint` | `ruff check .` + `ty check django_tiptap_editor` |
| `make lint-fix` | `ruff check --fix .` |
| `make format` / `make format-check` | write / verify `ruff format` |
| `make type-check` | `ty check django_tiptap_editor` |
| `make docs-serve` / `make docs-build` | live docs / strict build |
| `make release-bump VERSION=X.Y.Z` | bump `version.py` + promote CHANGELOG |
| `make release-publish` | workstation release (prepare → publish → finalize) |
| `make build-js` | rebuild the committed JS bundles (esbuild, in `js/`) |
| `make build` | `build-js` + `uv build` (sdist + wheel) |

## Structural rules

1. **One exported class or function per file.** File name = `snake_case` of the symbol.
   `TipTapWidget` → `tiptap_widget.py`; `get_default_config` → `get_default_config.py`,
   or live in a sibling `utils.py` if used by several files in the same package.
   **Exception:** a single `constants.py` per package is the only file allowed to export
   multiple symbols (enums, frozen settings defaults, reserved-key sets).
2. **Private helpers used in only one file** stay there with a leading `_`.
3. **Helpers shared across files** go under `utils/`. Non-exported infrastructure may sit
   in a sibling `utils.py`; the **exported config / settings readers and validators**
   (`get_default_config`, `get_asset_mode`, `get_extra_extensions`, `get_import_map`,
   `validate_config`, …) live one-per-file in the `utils/` subpackage and are re-exported
   from `utils/__init__.py`. Import them from their leaf path internally
   (`django_tiptap_editor.utils.get_default_config`).
4. **Top-level imports only.** No function-local / lazy imports unless a circular import
   is genuine and documented inline at the import site, or the dependency is optional —
   those imports go inside the function body with a clear `ImportError` message.
5. **Full type annotations on every function and method signature.** `Any` is allowed
   only at Django boundaries (e.g. `request`, form `attrs`, raw widget `value`) where the
   type genuinely is `Any`.
6. **`__init__.py` is the only re-export point.** Each `__init__.py` lists the public
   surface in `__all__`. Internal modules import from leaf paths, never from the
   package's `__init__`. The top-level `__init__.py` re-exports the user-facing API
   (widgets, admin widget, mixin, form field, config, template tags, upload view).
7. **Always `from __future__ import annotations`** at the top of any file with type
   annotations. We support Python 3.10+, so no `match` statements and no PEP 695 `type`
   statements.
8. **Absolute imports only.** Imports are ordered stdlib → third-party → first-party
   (`django_tiptap_editor`). Within each block, alphabetical.
9. **NEVER use relative imports.** `from . import x`, `from .foo import bar`, and any
   other dotted-relative form is forbidden everywhere, including `__init__.py`. Always
   write the full absolute path (`from django_tiptap_editor.foo import bar`).
10. **Types and functionality live in separate sub-packages.** When a directory contains
    *both* type declarations (dataclasses, frozen config records) *and* functionality
    (callables, registries), the types move into a `types/` sibling and are re-exported
    from the package's `__init__.py`. `constants.py` remains the multi-export exception.

## API style rules

- **Clean, options-object APIs.** No positional-argument tails. This is a fresh,
  semver-protected surface — do not clone TinyMCE's signatures.
- **Dataclasses over `dict[str, Any]` for structured data.** The config schema, asset-mode
  records, and any wire-shape payload are frozen `@dataclass`es with explicit field types.
  `dict[str, Any]` survives only at genuine serialisation boundaries (the
  `data-tiptap-config` JSON blob written into the textarea, raw widget `attrs`).
- **The package owns the editor; consumers own their domain.** Upload and image-list use
  conventional, documented contracts. App-specific behaviour (preview, merge-tag
  *resolution*, template rendering) is an extension point, never baked into the surface.

## JavaScript build (the one deviation)

The node toolchain lives **inside this package**, under `js/`. Built bundles are
**committed** to `django_tiptap_editor/static/` so consumers and their CI stay
Python-only. Every TipTap primitive is obtained through **one resolution point**
(`js/src/tiptap-runtime.ts`), never via scattered direct imports — that single seam is
what makes "bring your own TipTap" a build-config variant rather than a rewrite.

- One esbuild config (`js/esbuild.config.mjs`) emits **both** outputs:
  `tiptap.bundle.js` (IIFE, self-contained, default) and `tiptap.glue.esm.js` (glue
  only, `@tiptap/*` external). Both ship a matching `.css`.
- `make build-js` rebuilds both; `make build` depends on it. Outputs land in
  `django_tiptap_editor/static/django_tiptap_editor/` and are **committed**.
- The `js-build` CI job (`actions/setup-node`, `npm ci` against the committed
  lockfile) rebuilds and `git diff --exit-code`s the artifacts — a stale commit fails
  CI. esbuild output is deterministic for the pinned version, so the diff is reliable.
- After changing anything in `js/src/`, run `make build-js` and commit the regenerated
  bundles in the same change, or CI goes red.

In place today: the build pipeline, the runtime seam, and a minimal auto-mount editor.
The full extension set, registry, toolbar, and theming build on top of this seam.

## Tests

- `make test` runs pytest with `--cov=django_tiptap_editor --cov-fail-under=100` (line +
  branch). Restructure rather than reach for `# pragma: no cover`. Abstract bodies that
  genuinely cannot run (e.g. `BaseImageUploadView`'s `...` stubs) use a documented
  coverage-exclusion pragma so the 100% gate stays honest.
- Test layout mirrors the source tree under `tests/`. `django_tiptap_editor/foo/bar.py`
  → `tests/foo/test_bar.py`.
- `DJANGO_SETTINGS_MODULE=tests.conftest_settings`. DB tests use `@pytest.mark.django_db`.
- The **fidelity corpus** is the schema's test of record: a node/jsdom
  harness loads real, production-dumped TinyMCE HTML through the configured editor and
  serializes back, asserting no meaningful loss. It is built *first* and drives the
  schema design.

## Lint and types

- `make lint` runs `ruff check .` + `ty check django_tiptap_editor`. CI fails on either.
- `ruff format` is the source of truth for layout. `make format` writes, `make
  format-check` verifies.
- Use `...` (Ellipsis) over `pass` for empty bodies; logging over `print`.
- Pre-commit runs `make lint-fix`, `make format`, `make type-check`, plus a
  `forbid-local-paths` guard (no absolute home-directory paths or personal handles in
  committed text). Commits must be clean before push — never `--no-verify`.
- `ty` is scoped to `django_tiptap_editor/` only (not tests). For attributes provided by
  Django's MRO that ty can't resolve, declare them as `attr: Any` with a comment naming
  the parent.

## Compatibility floor

| | Minimum | Tested matrix |
| --- | --- | --- |
| Python | 3.10 | 3.10 – 3.14 |
| Django | 4.2 | 4.2, 5.0, 5.1, 5.2, 6.0 (supported-combos excludes baked into `tests.yml`) |
| TipTap | pinned per release | declared in `js/package.json`; a TipTap major bump that changes the primitive API is a major bump here too |

## Security stance (consumers render with `|safe`)

- ProseMirror's schema drops scripts/unknown nodes on parse — safer than TinyMCE.
- Link/image protocols are **allowlisted** (`linkProtocols`); `javascript:`/`data:`
  rejected. Uploaded `location` and picker `value` are validated before becoming `src`.
- Docs must enumerate exactly which tags/attributes/protocols survive, so `|safe` is
  justified. Custom-extension authors own the sanitization implications of anything new
  they introduce.

## Boundaries

- **Store HTML, never JSON.**
- **No consumer-app code**: no email pipeline, no preview view, no `email_template`, no
  app-specific models/routing. The package owns widget + bundle/glue + generic contracts
  + extension points.
- **No mandatory node dependency in consuming apps** — node lives only in this package's
  build; external mode uses CDN/import-maps, still node-free for the consumer.
- **Fresh package, fresh API** — compatibility with TinyMCE is the migration guide +
  fidelity corpus, not API shape.

## Branching

When working on a new feature or a version bump, **ALWAYS** switch to a new branch first
(`git checkout -b feat/...` or `release/vX.Y.Z`) and push to that branch. Never commit
feature work or version bumps directly to `main`, and never push to `main` from the local
checkout — `main` only advances via merged PRs (or, for releases, the tagged commit
produced by CI on the release commit).

## Releases

The release pipeline is **merge-to-main triggered**, not tag-triggered.
`.github/workflows/release.yml` runs on every push to `main` and calls
`make release-publish-prepare`. The script in
[`scripts/release-publish.sh`](scripts/release-publish.sh) is the single source of truth
and behaves as follows:

1. Extract the version from `django_tiptap_editor/version.py` (the single source of
   truth; `pyproject.toml` declares `dynamic = ["version"]` and hatchling reads it at
   build time).
2. Check whether `vX.Y.Z` already exists locally or on origin. **If yes → short-circuit**
   (`released=false`, exit 0). That is what makes every-merge-to-main safe.
3. Run `uv run pytest` as a final gate.
4. `uv build` into `dist/`.
5. Extract the `## [X.Y.Z]` section from `CHANGELOG.md` into the release notes.
6. Emit `released=true` so the downstream steps run: PyPI publish via **OIDC trusted
   publishing** (no token in repo), tag `vX.Y.Z` + GitHub Release, then
   `mkdocs gh-deploy` to `gh-pages`.

### First release / version bootstrap

The source tree carries **`0.0.0`** until the first publish; `[tool.bumpversion]
current_version` is `0.0.0` and the CHANGELOG footer starts at `compare/v0.0.0...HEAD`.
Cut the first release with `make release-bump VERSION=0.1.0`, which rewrites `version.py`,
promotes `[Unreleased]` → `[0.1.0]`, and fixes the compare-link footer.

### Cutting a release

```bash
# 1. On a release branch with CHANGELOG.md entries under ## [Unreleased]:
make release-bump VERSION=0.2.0
# 2. Review the diff, commit, open a PR, get it reviewed.
git diff && git commit -am "Release 0.2.0" && git push -u origin release/0.2.0 && gh pr create
# 3. Merge to main. release.yml detects the bump, runs the full flow, tags/publishes.
```

`release-bump` refuses to run on a dirty tree (`allow_dirty = false`). For an end-to-end
workstation release, `make release-publish` runs prepare → `uv publish` → finalize; set
`DRY_RUN=1` to rehearse.

### One-time setup (manual, by the repo owner)

1. **PyPI Trusted Publisher** — on PyPI, add a "Pending" publisher pointing at
   `Artui/django-tiptap-editor`, workflow `release.yml`, environment `pypi`.
2. **GitHub Environment** — create a `pypi` environment under `Settings → Environments`
   (no secrets; OIDC handles auth).
3. **GitHub Pages** — `Settings → Pages → Deploy from a branch → gh-pages → /`. The first
   docs deploy (or the `coverage-badge` job) creates the branch.
