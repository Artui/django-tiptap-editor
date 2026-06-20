// THE single TipTap resolution point.
//
// Every TipTap primitive the glue uses is obtained HERE, never via scattered
// direct imports elsewhere in src/. That single seam is what makes "bring your
// own TipTap" (the external asset mode) a build-config flip — esbuild marks
// `@tiptap/*` external for the glue build and these imports stay as bare
// specifiers, resolved by the consumer's import map. For the bundle build they
// are inlined. Either way the rest of the glue is byte-for-byte identical.
//
// This grows to re-export the resolved extension set (underline, text-style,
// color, background-color, link, image, table, sub/sup, and the custom
// paragraph / font-size extensions) as the editor is built out.
export { Editor, Extension, Mark, Node, mergeAttributes } from "@tiptap/core";
export { default as StarterKit } from "@tiptap/starter-kit";
