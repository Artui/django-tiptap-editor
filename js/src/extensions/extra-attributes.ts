// The attributes config.extraAttributes grants on built-in nodes (today `class`
// on paragraph and heading). Each is parsed from the element and written back
// verbatim, so it survives the source view and a stored value's re-parse. The
// server's EXTRA_ATTRIBUTE_TAGS / EXTRA_ATTRIBUTE_NAMES bound what a grant may
// name; test/extra-attributes.test.ts holds this side to the same table.
import { Extension } from "../tiptap-runtime";

export const EXTRA_ATTRIBUTE_TYPES: ReadonlySet<string> = new Set(["paragraph", "heading"]);
export const EXTRA_ATTRIBUTE_NAMES: ReadonlySet<string> = new Set(["class"]);

export type ExtraAttributesGrant = Record<string, string[]>;

function attribute(name: string) {
  return {
    default: null,
    parseHTML: (el: HTMLElement) => el.getAttribute(name) || null,
    renderHTML: (attrs: Record<string, unknown>) =>
      typeof attrs[name] === "string" && attrs[name] ? { [name]: attrs[name] } : {},
  };
}

export const ExtraAttributes = Extension.create<{ grant: ExtraAttributesGrant }>({
  name: "extraAttributes",
  addOptions() {
    return { grant: {} };
  },
  addGlobalAttributes() {
    return Object.entries(this.options.grant).map(([type, names]) => ({
      types: [type],
      attributes: Object.fromEntries(names.map((name) => [name, attribute(name)])),
    }));
  },
});

// The grant the editor mounts: only allowed types that this editor's schema
// holds, and only allowed attribute names, so a malformed config adds nothing.
export function resolveExtraAttributes(
  grant: ExtraAttributesGrant | undefined,
  enabled: (type: string) => boolean,
): ExtraAttributesGrant {
  const resolved: ExtraAttributesGrant = {};
  for (const [type, names] of Object.entries(grant ?? {})) {
    if (!EXTRA_ATTRIBUTE_TYPES.has(type) || !enabled(type) || !Array.isArray(names)) {
      continue;
    }
    const kept = [...new Set(names.filter((name) => EXTRA_ATTRIBUTE_NAMES.has(name)))];
    if (kept.length) {
      resolved[type] = kept;
    }
  }
  return resolved;
}
