.PHONY: help init test lint lint-fix format format-check type-check deps-bump build-js build docs-serve docs-build release-bump release-publish release-publish-prepare release-publish-finalize

help:
	@echo "Available targets:"
	@echo "  init             Sync deps (all groups) and install pre-commit hooks"
	@echo "  test             Run pytest with coverage (100% required)"
	@echo "  lint             Run ruff check + ty check"
	@echo "  lint-fix         Auto-fix lint issues with ruff"
	@echo "  format           Format with ruff"
	@echo "  format-check     Verify formatting"
	@echo "  type-check       Run ty over the package"
	@echo "  deps-bump        Upgrade pinned dependencies"
	@echo "  build-js         Rebuild the committed JS bundles (esbuild, in js/)"
	@echo "  build            build-js + uv build (sdist + wheel)"
	@echo "  docs-serve       Live-reload docs at http://localhost:8000 (needs mkdocs.yml)"
	@echo "  docs-build       Build docs into ./site (strict — fails on broken links)"
	@echo "  release-bump     Bump version files + CHANGELOG. Usage: make release-bump VERSION=X.Y.Z"
	@echo "  release-publish  prepare → uv publish → finalize (workstation release)"
	@echo "  release-publish-prepare   Run by release.yml on push to main (no-op unless bumped)"
	@echo "  release-publish-finalize  Tag vX.Y.Z + create GitHub Release after PyPI publish"

init:
	uv sync --all-groups
	uv run pre-commit install

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ty check django_tiptap_editor

lint-fix:
	uv run ruff check --fix .

format:
	uv run ruff format .

format-check:
	uv run ruff format --check --diff .

type-check:
	uv run ty check django_tiptap_editor

deps-bump:
	uvx uv-upx upgrade run --profile with_pinned

# Embedded esbuild build. The node toolchain lives inside js/; the built
# bundles are committed under django_tiptap_editor/static/ so consumers and
# their CI stay Python-only. CI rebuilds and diffs them to catch staleness.
build-js:
	cd js && npm install && npm run build

build: build-js
	uv build

docs-serve:
	uv run --group docs mkdocs serve

docs-build:
	uv run --group docs mkdocs build --strict

release-bump:
	@if [ -z "$(VERSION)" ]; then \
		echo "Usage: make release-bump VERSION=X.Y.Z"; exit 1; \
	fi
	uvx bump-my-version bump --new-version "$(VERSION)" patch
	$(MAKE) build-js
	@echo ""
	@echo "Bumped to $(VERSION) and rebuilt JS bundles (version baked in)."
	@echo "Edit CHANGELOG.md to fill the new section, review with 'git diff',"
	@echo "then run 'make release-publish'."

# Release pipeline. The version lives in django_tiptap_editor/version.py
# (pyproject pulls it in via [tool.hatch.version] dynamic). The three targets
# below wrap scripts/release-publish.sh, which is the single source of truth
# for the flow and stays byte-identical across the sibling repos.
#
#   release-publish-prepare   — version short-circuit, pytest, uv build, extract
#                               CHANGELOG section. Called by release.yml on every
#                               push to main; no-ops unless the version was
#                               bumped past the most recent vX.Y.Z tag.
#   release-publish-finalize  — tag vX.Y.Z, push it, create the GitHub Release.
#                               Called after PyPI publish succeeds in CI.
#   release-publish           — prepare → uv publish → finalize. For end-to-end
#                               workstation releases. Set DRY_RUN=1 to rehearse.
RELEASE_PACKAGE_NAME := django-tiptap-editor
RELEASE_VERSION_FILES := django_tiptap_editor/version.py|^__version__[^=]*= *

release-publish:
	@PACKAGE_NAME='$(RELEASE_PACKAGE_NAME)' \
	VERSION_FILES="$$(printf '$(RELEASE_VERSION_FILES)')" \
		bash scripts/release-publish.sh all

release-publish-prepare:
	@PACKAGE_NAME='$(RELEASE_PACKAGE_NAME)' \
	VERSION_FILES="$$(printf '$(RELEASE_VERSION_FILES)')" \
		bash scripts/release-publish.sh prepare

release-publish-finalize:
	@PACKAGE_NAME='$(RELEASE_PACKAGE_NAME)' \
	VERSION_FILES="$$(printf '$(RELEASE_VERSION_FILES)')" \
		bash scripts/release-publish.sh finalize
