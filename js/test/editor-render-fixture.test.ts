// Generates tests/utils/fixtures/editor_render.json from the editor itself.
//
// The Python side renders and sanitises what the editor produces, so its
// fixtures have to come from the editor rather than from someone's idea of it.
// Each case is a small document; the fixture records:
//
//   doc         the editor's own JSON for it (what TipTapJSONField stores);
//   html        the editor's getHTML() (what the HTML storage path stores);
//   attributes  the attributes Tiptap's renderHTML gives the case's element,
//               in order and before the browser re-serialises any style, which
//               is the form render_doc writes.
//
// tests/utils/test_render_doc.py holds render_doc to `attributes`, and
// tests/utils/test_sanitize_html.py holds the sanitiser to keeping `html` byte
// for byte. The cases cover the attributes Tiptap 3 began rendering (a link
// title, table-cell alignment); attributes render_doc already orders or omits
// differently from the editor are kept out of them on purpose, so a case fails
// for the attribute it names.
//
// A normal run regenerates the fixture and fails if it differs from the
// committed file. To rewrite it after a deliberate change:
//
//   UPDATE_EDITOR_RENDER_FIXTURE=1 npx vitest run test/editor-render-fixture.test.ts
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { expect, it } from "vitest";

import { buildExtensions } from "../src/build-extensions";
import { Editor } from "../src/tiptap-runtime";

// Joined from the module's path string: under the jsdom environment the global
// URL is jsdom's, which fileURLToPath does not accept.
const FIXTURE = join(
  dirname(fileURLToPath(import.meta.url)),
  "../../tests/utils/fixtures/editor_render.json",
);

type Json = Record<string, unknown>;
type Case = { name: string; target: { node?: string; mark?: string }; doc: Json };

const text = (marks?: Json[]): Json => ({ type: "text", text: "x", ...(marks ? { marks } : {}) });
const paragraph = (...content: Json[]): Json => ({ type: "paragraph", content });
const doc = (...content: Json[]): Json => ({ type: "doc", content });
const table = (type: string, attrs: Json): Json =>
  doc({
    type: "table",
    content: [{ type: "tableRow", content: [{ type, attrs, content: [paragraph(text())] }] }],
  });
const link = (attrs: Json): Json => doc(paragraph(text([{ type: "link", attrs }])));

const CASES: Case[] = [
  {
    name: "link with a title",
    target: { mark: "link" },
    doc: link({ href: "https://example.test/", title: 'Say "hi" & wave' }),
  },
  { name: "link without a title", target: { mark: "link" }, doc: link({ href: "https://example.test/" }) },
  ...(["left", "center", "right"] as const).map((align) => ({
    name: `table cell aligned ${align}`,
    target: { node: "tableCell" },
    doc: table("tableCell", { align }),
  })),
  { name: "table header aligned right", target: { node: "tableHeader" }, doc: table("tableHeader", { align: "right" }) },
  {
    name: "table cell spanning two columns, aligned",
    target: { node: "tableCell" },
    doc: table("tableCell", { colspan: 2, align: "center" }),
  },
  {
    // Tiptap accepts only left, right and center for a cell and renders
    // nothing for any other value, so render_doc must not render it either.
    name: "table cell with an alignment the editor does not render",
    target: { node: "tableCell" },
    doc: table("tableCell", { align: "justify" }),
  },
];

function generate(): string {
  const editor = new Editor({
    element: document.createElement("div"),
    content: "",
    extensions: buildExtensions({}, { tiptap: {}, locale: "en", t: (k) => k }),
  });
  const cases = CASES.map(({ name, target, doc: input }) => {
    editor.commands.setContent(input, { emitUpdate: false });
    let spec: unknown;
    editor.state.doc.descendants((node) => {
      if (spec !== undefined) {
        return false;
      }
      if (target.node && node.type.name === target.node) {
        spec = node.type.spec.toDOM?.(node);
      }
      const mark = target.mark ? node.marks.find((m) => m.type.name === target.mark) : undefined;
      if (mark) {
        spec = mark.type.spec.toDOM?.(mark, true);
      }
      return true;
    });
    const [tag, maybeAttrs] = spec as [string, unknown];
    const attrs = maybeAttrs && typeof maybeAttrs === "object" && !Array.isArray(maybeAttrs) ? maybeAttrs : {};
    // ProseMirror skips null and undefined, and setAttribute stringifies the rest.
    const attributes = Object.entries(attrs as Json)
      .filter(([, value]) => value != null)
      .map(([key, value]) => [key, String(value)]);
    return { name, doc: editor.getJSON(), html: editor.getHTML(), tag, attributes };
  });
  editor.destroy();
  return `${JSON.stringify({ generatedBy: "js/test/editor-render-fixture.test.ts", cases }, null, 2)}\n`;
}

it("the committed editor-render fixture is what the editor renders today", () => {
  const fresh = generate();
  if (process.env.UPDATE_EDITOR_RENDER_FIXTURE) {
    writeFileSync(FIXTURE, fresh);
  }
  expect(readFileSync(FIXTURE, "utf8")).toBe(fresh);
});
