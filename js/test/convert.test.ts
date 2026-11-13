// HTML <-> JSON converters used by the JSON-storage helpers and the migration
// path. They run against the package's exact extension set, so parsing applies
// the same schema normalization the editor does on load.
import { describe, expect, it } from "vitest";

import { htmlToJSON, htmlToStored, renderHTML } from "../src/convert";
import { registerExtension } from "../src/registry";

describe("html <-> json conversion", () => {
  it("parses HTML into a ProseMirror doc", () => {
    const doc = htmlToJSON("<p>Hello <strong>world</strong></p>") as {
      type: string;
      content: unknown[];
    };
    expect(doc.type).toBe("doc");
    expect(JSON.stringify(doc)).toContain("bold");
    expect(JSON.stringify(doc)).toContain("world");
  });

  it("renders a doc back to HTML", () => {
    const doc = htmlToJSON("<p>Hello <strong>world</strong></p>");
    expect(renderHTML(doc)).toBe("<p>Hello <strong>world</strong></p>");
  });

  it("htmlToStored returns a {doc, html} envelope with a normalized mirror", () => {
    const stored = htmlToStored("<p>x</p>");
    expect(stored.doc).toMatchObject({ type: "doc" });
    expect(stored.html).toBe("<p>x</p>");
  });

  it("applies schema normalization on conversion (div -> paragraph)", () => {
    // A legacy-editor-ism with no schema node: <div> maps to a paragraph.
    expect(htmlToStored("<div>legacy</div>").html).toBe("<p>legacy</p>");
  });

  describe("a factory that reads ctx.tiptap", () => {
    const config = { extensions: ["ctx-mark"] };
    registerExtension("ctx-mark", (_cfg, ctx) => {
      const { Mark } = ctx.tiptap as { Mark: { create: (o: object) => never } };
      return Mark.create({
        name: "ctxMark",
        parseHTML: () => [{ tag: "mark.ctx" }],
        renderHTML: () => ["mark", { class: "ctx" }, 0],
      });
    });
    const html = '<p><mark class="ctx">x</mark></p>';

    it("htmlToJSON builds the extension", () => {
      expect(JSON.stringify(htmlToJSON(html, config))).toContain("ctxMark");
    });

    it("renderHTML builds the extension", () => {
      expect(renderHTML(htmlToJSON(html, config), config)).toBe(html);
    });

    it("htmlToStored builds the extension", () => {
      expect(htmlToStored(html, config).html).toBe(html);
    });
  });

  describe("the extending guide's Node factory", () => {
    const config = { extensions: ["ctx-callout"] };
    registerExtension("ctx-callout", (_cfg, ctx) => {
      const { Node, mergeAttributes } = ctx.tiptap as {
        Node: { create: (o: object) => never };
        mergeAttributes: (...a: object[]) => object;
      };
      return Node.create({
        name: "callout",
        group: "block",
        content: "block+",
        parseHTML: () => [{ tag: "aside.callout" }],
        renderHTML: ({ HTMLAttributes }: { HTMLAttributes: object }) => [
          "aside",
          mergeAttributes(HTMLAttributes, { class: "callout" }),
          0,
        ],
      });
    });
    const html = '<aside class="callout"><p>x</p></aside>';

    it("htmlToJSON builds the extension", () => {
      expect(JSON.stringify(htmlToJSON(html, config))).toContain('"callout"');
    });

    it("renderHTML builds the extension", () => {
      expect(renderHTML(htmlToJSON(html, config), config)).toBe(html);
    });

    it("htmlToStored builds the extension", () => {
      expect(htmlToStored(html, config).html).toBe(html);
    });
  });
});
