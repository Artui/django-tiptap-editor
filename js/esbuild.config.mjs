// One config, two committed outputs:
//
//   tiptap.bundle.js   — IIFE, self-contained (TipTap inlined). Default asset
//                        mode; fully node-free for consumers.
//   tiptap.glue.esm.js — ESM, @tiptap/* left external. For consumers who bring
//                        TipTap via CDN / import maps (external asset mode).
//
// The ONLY difference between the two is whether the imports funnelled through
// src/tiptap-runtime.ts are inlined or left external. esbuild output is
// deterministic for a pinned version, so CI rebuilds and diffs the committed
// artifacts to catch staleness.
import { readFileSync } from "node:fs";

import { build } from "esbuild";

// The TipTap version the bundle was built + the fidelity corpus validated
// against. Baked into the glue so it can warn on external-mode version skew.
const TIPTAP_VERSION = JSON.parse(
  readFileSync("node_modules/@tiptap/core/package.json", "utf8"),
).version;

// The package version, read from the single source of truth (version.py) and
// baked into the bundle as DjangoTipTap.version. CI's js-build diff check then
// enforces that a committed bundle carries the current version — so `make
// release-bump` rebuilds the bundle after bumping version.py.
const PACKAGE_VERSION = /__version__\s*:\s*str\s*=\s*"([^"]+)"/.exec(
  readFileSync("../django_tiptap_editor/version.py", "utf8"),
)?.[1];
if (!PACKAGE_VERSION) {
  throw new Error("could not read __version__ from ../django_tiptap_editor/version.py");
}

const OUTDIR = "../django_tiptap_editor/static/django_tiptap_editor";

const shared = {
  bundle: true,
  minify: true,
  sourcemap: false,
  target: ["es2020"],
  legalComments: "none",
  logLevel: "info",
};

const defines = (buildKind) => ({
  __DTT_VERSION__: JSON.stringify(PACKAGE_VERSION),
  __DTT_TIPTAP_VERSION__: JSON.stringify(TIPTAP_VERSION),
  __DTT_BUILD__: JSON.stringify(buildKind),
});

// 1) Self-contained IIFE bundle (default).
await build({
  ...shared,
  entryPoints: ["src/index.ts"],
  outfile: `${OUTDIR}/tiptap.bundle.js`,
  format: "iife",
  define: defines("bundle"),
});

// 2) Glue-only ESM with TipTap externalised (bring-your-own-TipTap).
await build({
  ...shared,
  entryPoints: ["src/index.ts"],
  outfile: `${OUTDIR}/tiptap.glue.esm.js`,
  format: "esm",
  external: ["@tiptap/*"],
  define: defines("glue"),
});

console.log(`built tiptap.bundle.{js,css} + tiptap.glue.esm.{js,css} (TipTap ${TIPTAP_VERSION})`);
