// Per-field feature sets: which built-in extensions a field mounts at all. A
// toolbar only hides buttons, so restricting what a field can contain means not
// mounting the rest: an extension that is absent has no node or mark in the
// schema, so its input rules, keyboard shortcuts and paste parsing go with it.
//
// On the Django path the server has already resolved the list (core and
// dependencies included) before writing it into data-tiptap-config; resolving it
// again here is a no-op. init(config) bypasses the server, so the model is
// restated below, and test/features.test.ts holds it equal to the one the Python
// side exports (test/fixtures/feature-model.json).
import type { TipTapConfig } from "./default-config";

// What every field with a `features` list gets regardless: the structure every
// document needs, undo, the two cursors, and hardBreak (Shift-Enter inside a list
// item and a pasted <br> both need it).
export const FEATURE_CORE: ReadonlySet<string> = new Set<string>([
  "document",
  "text",
  "paragraph",
  "hardBreak",
  "history",
  "dropcursor",
  "gapcursor",
]);

// Features that cannot work without another; listing a key pulls in its values.
// `highlight` is the backgroundColor attribute under its toolbar name.
export const FEATURE_DEPENDENCIES: Readonly<Record<string, readonly string[]>> = {
  bulletList: ["listItem"],
  orderedList: ["listItem"],
  table: ["tableRow", "tableCell", "tableHeader"],
  fontFamily: ["textStyle"],
  color: ["textStyle"],
  backgroundColor: ["textStyle"],
  highlight: ["backgroundColor", "textStyle"],
  fontSize: ["textStyle"],
};

// Whether a control that needs `feature` (ButtonSpec.requires) can run on a
// field whose resolved features are `features`. A control needing nothing runs
// everywhere, and an unrestricted field (null) has every feature. Each clause
// has a test in test/restrict-features.test.ts that fails without it: "leaves
// consumer-registered buttons alone" (undefined), the "unchanged" cases (null)
// and "renders none of the excluded buttons by default" (has).
export function featureEnabled(features: Set<string> | null, feature: string | undefined): boolean {
  return feature === undefined || features === null || features.has(feature);
}

// Every feature `config` turns on, or null when it restricts none. null is the
// unrestricted editor: no `features` key (or null, which the server treats the
// same way), so the whole baseline mounts exactly as it always has. A list is a
// restriction: the list, the core, and the closure of its dependencies. The walk
// stops at anything already seen, which is what makes a pre-resolved list a no-op
// and a cycle harmless.
export function resolveFeatures(config: TipTapConfig): Set<string> | null {
  const features = config.features;
  if (features == null) {
    return null;
  }
  const resolved = new Set<string>(FEATURE_CORE);
  const pending = [...features];
  while (pending.length > 0) {
    const name = pending.pop() as string;
    if (resolved.has(name)) {
      continue;
    }
    resolved.add(name);
    pending.push(...(FEATURE_DEPENDENCIES[name] ?? []));
  }
  return resolved;
}
