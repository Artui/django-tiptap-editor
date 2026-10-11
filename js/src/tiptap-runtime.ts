// THE single TipTap resolution point.
//
// Every TipTap primitive AND vendored extension the glue uses is obtained HERE,
// never via scattered direct imports elsewhere in src/. That single seam is what
// makes "bring your own TipTap" (the external asset mode) a build-config flip —
// esbuild marks `@tiptap/*` external for the glue build and these imports stay
// as bare specifiers, resolved by the consumer's import map. For the bundle
// build they are inlined. Either way the rest of the glue is byte-for-byte
// identical, and our custom extensions import their primitives from here.

// Primitives (for custom-extension authors).
export { Editor, Extension, Mark, Node, mergeAttributes } from "@tiptap/core";

// HTML <-> ProseMirror-JSON converters (browser; the bundle runs in the browser
// and the glue resolves @tiptap/core via the consumer's import map). Power the
// JSON storage helpers and the HTML->JSON migration path.
export { generateHTML, generateJSON } from "@tiptap/core";

// The schema an extension set produces, without mounting an editor. Lets the
// JSON-storage load check a stored doc against the field's own schema first.
export { getSchema } from "@tiptap/core";

// Structural baseline.
export { default as StarterKit } from "@tiptap/starter-kit";

// Vendored feature extensions (the fidelity set proven against the corpus).
export { default as Underline } from "@tiptap/extension-underline";
export { TextStyle } from "@tiptap/extension-text-style";
export { default as FontFamily } from "@tiptap/extension-font-family";
export { default as Color } from "@tiptap/extension-color";
export { default as TextAlign } from "@tiptap/extension-text-align";
export { default as Link } from "@tiptap/extension-link";
export { default as Image } from "@tiptap/extension-image";
export { Table } from "@tiptap/extension-table";
export { default as TableRow } from "@tiptap/extension-table-row";
export { default as TableCell } from "@tiptap/extension-table-cell";
export { default as TableHeader } from "@tiptap/extension-table-header";
export { default as Subscript } from "@tiptap/extension-subscript";
export { default as Superscript } from "@tiptap/extension-superscript";
// Tiptap 3 moved CharacterCount into @tiptap/extensions and keeps the old
// package only as a re-export of it. Importing the real home means external
// mode resolves one module for it, and the same one StarterKit already uses.
export { CharacterCount } from "@tiptap/extensions";
