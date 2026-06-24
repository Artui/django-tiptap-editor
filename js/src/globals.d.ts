// esbuild `define` injections (see esbuild.config.mjs).
declare const __DTT_VERSION__: string;
declare const __DTT_TIPTAP_VERSION__: string;
declare const __DTT_BUILD__: string;

// Side-effect CSS imports (e.g. `import "./styles.css"` in index.ts) are handled
// by esbuild at build time. The pinned TypeScript (5.7.x, moduleResolution
// "Bundler") tolerates them, but TS >= 5.8 reports TS2882 without this ambient
// declaration — so declare it to keep `npm run typecheck` green across upgrades.
declare module "*.css";
