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
import { build } from "esbuild";

const OUTDIR = "../django_tiptap_editor/static/django_tiptap_editor";

const shared = {
  bundle: true,
  minify: true,
  sourcemap: false,
  target: ["es2020"],
  legalComments: "none",
  logLevel: "info",
};

// 1) Self-contained IIFE bundle (default).
await build({
  ...shared,
  entryPoints: ["src/index.ts"],
  outfile: `${OUTDIR}/tiptap.bundle.js`,
  format: "iife",
});

// 2) Glue-only ESM with TipTap externalised (bring-your-own-TipTap).
await build({
  ...shared,
  entryPoints: ["src/index.ts"],
  outfile: `${OUTDIR}/tiptap.glue.esm.js`,
  format: "esm",
  external: ["@tiptap/*"],
});

console.log("built tiptap.bundle.{js,css} + tiptap.glue.esm.{js,css}");
