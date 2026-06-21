// HTML <-> JSON converters used by the JSON-storage helpers and the migration
// path. They run against the package's exact extension set, so parsing applies
// the same schema normalization the editor does on load.
import { describe, expect, it } from "vitest";

import { htmlToJSON, htmlToStored, renderHTML } from "../src/convert";

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
    // A TinyMCE-ism with no schema node: <div> maps to a paragraph.
    expect(htmlToStored("<div>legacy</div>").html).toBe("<p>legacy</p>");
  });
});
