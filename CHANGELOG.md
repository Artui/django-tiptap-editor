# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-06-20

### Added

- **Django integration**: `TipTapWidget`, `AdminTipTapWidget`,
  `TipTapModelAdminMixin`, and `TipTapFormField`. Stores HTML (render with
  `|safe`); the ProseMirror schema sanitizes on parse (scripts/unknown nodes
  dropped, link/image protocol allowlists).
- **Editor**: full toolbar — formatting, font size/family, text colour,
  highlight, headings, lists, alignment, links, images, tables, and a raw-HTML
  source view — plus a button registry (`ui.registerButton`) and design-token
  theming (`--tiptap-*` / `ui.setTokens`).
- **Images & content**: upload (toolbar/paste/drop, CSRF, protocol-validated)
  with the `{file} → {location}` contract, a library picker, merge tags, an
  `onChange` callback (explicit init / Path B), and `BaseImageUploadView` /
  `ImageUploadError` helpers.
- **Extensibility & i18n**: `registerExtension` (+ `TIPTAP_EXTRA_EXTENSIONS`),
  en/sv locales with `registerLocale`, and re-exported TipTap primitives for
  no-build authoring.
- **Asset modes**: a committed, self-contained bundle (default, node-free) and a
  glue-only ESM build for bring-your-own-TipTap via import maps, with a default
  CDN import map and a startup version-skew check.
- **Settings**: `TIPTAP_DEFAULT_CONFIG`, `TIPTAP_ASSET_MODE`,
  `TIPTAP_IMPORT_MAP`, `TIPTAP_EXTRA_EXTENSIONS`; `{% tiptap_media %}` and
  `{% tiptap_config %}` template tags.
- **Quality**: a TinyMCE-corpus round-trip fidelity test, 100% line+branch
  Python coverage, and full documentation.

[Unreleased]: https://github.com/Artui/django-tiptap-editor/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Artui/django-tiptap-editor/compare/v0.0.0...v0.1.0
