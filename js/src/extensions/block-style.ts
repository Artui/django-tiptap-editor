// Typed block-style attributes recovered from the fidelity corpus: legacy
// editors (e.g. TinyMCE for email) emit inline margin / indent on paragraphs
// and headings, which the default schema drops. These are typed attributes
// (not an opaque style passthrough) so the sanitization story stays clean; each
// renders its own style fragment and merges with text-align on the same node.
import { Extension } from "../tiptap-runtime";

export const BlockStyle = Extension.create({
  name: "blockStyle",
  addOptions() {
    return { types: ["paragraph", "heading"] };
  },
  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: {
          margin: {
            default: null,
            parseHTML: (el: HTMLElement) => el.style.margin || null,
            renderHTML: (attrs: Record<string, unknown>) =>
              attrs.margin ? { style: `margin: ${attrs.margin as string}` } : {},
          },
          marginBlockEnd: {
            default: null,
            parseHTML: (el: HTMLElement) => el.style.marginBlockEnd || null,
            renderHTML: (attrs: Record<string, unknown>) =>
              attrs.marginBlockEnd
                ? { style: `margin-block-end: ${attrs.marginBlockEnd as string}` }
                : {},
          },
          paddingLeft: {
            default: null,
            parseHTML: (el: HTMLElement) => el.style.paddingLeft || null,
            renderHTML: (attrs: Record<string, unknown>) =>
              attrs.paddingLeft ? { style: `padding-left: ${attrs.paddingLeft as string}` } : {},
          },
        },
      },
    ];
  },
});
