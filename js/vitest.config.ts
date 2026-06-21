import { defineConfig } from "vitest/config";

export default defineConfig({
  // Mirror the esbuild `define` injections (see esbuild.config.mjs) so modules
  // that read them — e.g. version-check.ts — import cleanly under vitest.
  define: {
    __DTT_TIPTAP_VERSION__: '"2.27.2"',
    __DTT_BUILD__: '"bundle"',
  },
  test: {
    environment: "jsdom",
    include: ["test/**/*.test.ts"],
  },
});
