import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

// Read the package version from the single source of truth, matching the esbuild
// build (see esbuild.config.mjs).
const packageVersion = /__version__\s*:\s*str\s*=\s*"([^"]+)"/.exec(
  readFileSync(fileURLToPath(new URL("../django_tiptap_editor/version.py", import.meta.url)), "utf8"),
)?.[1];

export default defineConfig({
  // Mirror the esbuild `define` injections (see esbuild.config.mjs) so modules
  // that read them — e.g. version-check.ts, index.ts — import cleanly under vitest.
  define: {
    __DTT_VERSION__: JSON.stringify(packageVersion),
    __DTT_TIPTAP_VERSION__: '"2.27.2"',
    __DTT_BUILD__: '"bundle"',
  },
  test: {
    environment: "jsdom",
    include: ["test/**/*.test.ts"],
  },
});
