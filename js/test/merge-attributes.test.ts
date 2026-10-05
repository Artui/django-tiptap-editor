// mergeAttributes as extension authors receive it: the one on
// DjangoTipTap.tiptap and ctx.tiptap, which is Tiptap's own, re-exported from
// the runtime seam and shipped inside the bundle. docs/extending.md builds a
// custom node's attributes with it, so what it does with a hostile argument is
// part of what this package ships, not only part of what it depends on.
import { describe, expect, it } from "vitest";

import { Editor, Node, StarterKit, mergeAttributes } from "../src/tiptap-runtime";

// JSON is where an own "__proto__" key comes from: an object literal would set
// the prototype instead, and JSON.parse is how attributes stored in content
// arrive.
const HOSTILE = '{"__proto__": {"onclick": "alert(1)"}}';

describe("mergeAttributes", () => {
  it("keeps an own __proto__ key as data instead of the result's prototype", () => {
    const merged = mergeAttributes({ class: "callout" }, JSON.parse(HOSTILE));

    expect(Object.getPrototypeOf(merged)).toBe(Object.prototype);
    expect("onclick" in merged).toBe(false);
    expect(merged.class).toBe("callout");
  });

  it("lets no inherited handler reach the rendered element", () => {
    // The extending.md pattern, with the second argument taken from the
    // document rather than written by hand. ProseMirror's serializer walks the
    // attribute object with for...in, so an inherited key renders like an own
    // one -- which is how a swapped prototype becomes an event handler.
    const Embed = Node.create({
      name: "embed",
      group: "inline",
      inline: true,
      atom: true,
      addAttributes: () => ({ extra: { default: {}, renderHTML: () => ({}) } }),
      renderHTML: ({ node, HTMLAttributes }) => [
        "span",
        mergeAttributes(HTMLAttributes, node.attrs.extra as Record<string, unknown>),
      ],
    });
    const editor = new Editor({
      extensions: [StarterKit, Embed],
      content: {
        type: "doc",
        content: [
          {
            type: "paragraph",
            content: [{ type: "embed", attrs: { extra: JSON.parse(HOSTILE) } }],
          },
        ],
      },
    });

    expect(editor.getHTML()).not.toContain("onclick");
    expect(editor.view.dom.querySelector("[onclick]")).toBeNull();

    editor.destroy();
  });
});
