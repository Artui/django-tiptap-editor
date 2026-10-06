// docs/asset-modes.md lists what a TIPTAP_IMPORT_MAP override has to resolve:
// the specifiers the glue imports, then the ones the packages' own dist/ files
// import in turn, which a self-hosted map needs and a rewriting CDN does not.
// Both lists change with every Tiptap upgrade (Tiptap 3 moved CharacterCount
// into @tiptap/extensions and folded the list extensions into
// @tiptap/extension-list), so they are regenerated here from the installed
// packages rather than trusted. The Python side holds GLUE_IMPORT_SPECIFIERS to
// the built glue in tests/utils/test_get_import_map.py.
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { expect, it } from "vitest";

const HERE = dirname(fileURLToPath(import.meta.url));
const MODULES = join(HERE, "../node_modules");

// Bare specifiers in a module's import and re-export statements. Anchored to a
// statement start, and limited to valid package names, because these files
// also carry the words in strings and comments.
const STATEMENT = /^\s*(?:import|export)\b[^"';]*?["']([^"']+)["']/gm;
const PACKAGE_NAME = /^(@[a-z0-9][a-z0-9._-]*\/)?[a-z0-9][a-z0-9._-]*(\/[a-z0-9._/-]+)?$/;

function bareImports(source: string): string[] {
  return [...source.matchAll(STATEMENT)].map((m) => m[1]).filter((s) => PACKAGE_NAME.test(s));
}

type Exports = string | { import?: Exports; module?: Exports; default?: Exports } | undefined;

// The ESM file a browser import map would point a specifier at.
function entryFile(specifier: string): string {
  const depth = specifier.startsWith("@") ? 2 : 1;
  const name = specifier.split("/").slice(0, depth).join("/");
  const subpath = specifier.slice(name.length);
  const manifest = JSON.parse(readFileSync(join(MODULES, name, "package.json"), "utf8"));
  const pick = (value: Exports): string | undefined =>
    typeof value === "string" ? value : value && (pick(value.import) ?? pick(value.module) ?? pick(value.default));
  const exported = manifest.exports?.[`.${subpath}`] ?? (subpath ? undefined : manifest.exports);
  const file = pick(exported) ?? (subpath ? undefined : (manifest.module ?? manifest.main));
  if (!file || !existsSync(join(MODULES, name, file))) {
    throw new Error(`no ESM entry for ${specifier}`);
  }
  return join(MODULES, name, file);
}

// The two ```text blocks in the page's override section, in order.
function documentedLists(): [string[], string[]] {
  const page = readFileSync(join(HERE, "../../docs/asset-modes.md"), "utf8");
  const section = page.split("### Overriding the map, and self-hosting")[1]?.split("\n### ")[0] ?? "";
  const blocks = [...section.matchAll(/```text\n([\s\S]*?)```/g)].map((m) => m[1].trim().split("\n"));
  expect(blocks, "the page should carry exactly two ```text lists").toHaveLength(2);
  return [blocks[0], blocks[1]];
}

it("documents exactly the specifiers the glue imports", () => {
  const runtime = readFileSync(join(HERE, "../src/tiptap-runtime.ts"), "utf8");
  const [glue] = documentedLists();
  expect(glue).toEqual([...new Set(bareImports(runtime))]);
});

it("documents exactly what a map of the packages' own dist files must also resolve", () => {
  const [glue, transitive] = documentedLists();
  const seen = new Set<string>();
  const queue = [...glue];
  while (queue.length) {
    const specifier = queue.shift() as string;
    if (!seen.has(specifier)) {
      seen.add(specifier);
      queue.push(...bareImports(readFileSync(entryFile(specifier), "utf8")));
    }
  }
  const needed = [...seen].filter((s) => !glue.includes(s));
  // @tiptap/* first, then the rest, each alphabetical: the page's order.
  const order = (s: string) => `${s.startsWith("@tiptap/") ? 0 : 1}${s}`;
  expect(transitive).toEqual(needed.sort((a, b) => order(a).localeCompare(order(b))));
});
