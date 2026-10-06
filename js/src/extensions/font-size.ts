// font-size as a TextStyle attribute, written when Tiptap 2 had no official
// extension (Tiptap 3's text-style package now exports one). Symmetric with
// color / font-family / background-color: parses `span[style*=font-size]` and
// renders `<span style="font-size: …">`.
import { Extension } from "../tiptap-runtime";

export const FontSize = Extension.create({
  name: "fontSize",
  addOptions() {
    return { types: ["textStyle"] };
  },
  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: {
          fontSize: {
            default: null,
            parseHTML: (el: HTMLElement) => el.style.fontSize || null,
            renderHTML: (attrs: Record<string, unknown>) =>
              attrs.fontSize ? { style: `font-size: ${attrs.fontSize as string}` } : {},
          },
        },
      },
    ];
  },
});
