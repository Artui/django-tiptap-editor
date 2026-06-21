# Versioning & stability

This project follows [Semantic Versioning](https://semver.org). Releases are recorded in
the [CHANGELOG](https://github.com/Artui/django-tiptap-editor/blob/main/CHANGELOG.md).

## Surface stability

| Surface | Stability |
| --- | --- |
| Python widget / admin mixin / form field / settings | **Stable** |
| Config schema (keys) | **Stable** (additive) |
| `DjangoTipTap` JS API (`init`/`get`/`destroy`/`autoMount`/`registerExtension`/`registerLocale`) | **Stable** |
| Toolbar button registry (`ui.registerButton`) + button keys | **Stable** |
| Design tokens (`--tiptap-*`) + namespaced part classes | **Stable** |
| Custom-extension API (via `DjangoTipTap.tiptap`) | **Tied to the TipTap major** |
| Region renderers (`ui.setRenderer` — `"toolbar"` / `"statusbar"`) | **Semi-stable** (the `ctx` shape may grow additively; breaking changes are called out) |
| Shell renderer (`ui.setShellRenderer`) | **Experimental** — most likely to change across minors |

## TipTap coupling

Extensions are tied to a TipTap major version. The supported TipTap version is declared
per release (and exposed as `DjangoTipTap.supportedTipTapVersion`). A TipTap major bump
that changes the primitive API is a **major** bump here too.

## Lossless guarantee

The fidelity (lossless round-trip) guarantee ships for the **bundled** TipTap version. In
[external asset mode](asset-modes.md) you own re-running the fidelity corpus against your
chosen version — the startup console check reminds you.

## Pre-1.0

While on `0.x`, minor versions may include breaking changes to surfaces marked above as
not yet stable; they will be called out in the changelog.
