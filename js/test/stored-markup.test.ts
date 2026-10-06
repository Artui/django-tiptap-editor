// Two changes Tiptap 3 makes to what gets stored, as the upgrade note in the
// CHANGELOG describes them. Both are content-preserving, and both are visible
// to anyone diffing stored values across the upgrade.
import { describe, expect, it } from "vitest";

import { buildExtensions } from "../src/build-extensions";
import { Editor } from "../src/tiptap-runtime";

function roundTrip(html: string): Editor {
  const editor = new Editor({
    element: document.createElement("div"),
    content: "",
    extensions: buildExtensions({}, { tiptap: {}, locale: "en", t: (k) => k }),
  });
  editor.commands.setContent(html, { emitUpdate: false });
  return editor;
}

describe("stored markup under Tiptap 3", () => {
  it("drops a cell's default colspan and rowspan from the HTML", () => {
    const editor = roundTrip('<table><tbody><tr><td colspan="1" rowspan="1"><p>a</p></td></tr></tbody></table>');
    expect(editor.getHTML()).toContain("<td><p>a</p></td>");
    editor.destroy();
  });

  it("keeps a colour as written in the JSON, while the HTML stays rgb()", () => {
    const editor = roundTrip('<p><span style="color: #ff0000">a</span></p>');
    const marks = (editor.getJSON().content?.[0].content?.[0].marks ?? []) as { attrs?: { color?: string } }[];
    expect(marks[0]?.attrs?.color).toBe("#ff0000");
    expect(editor.getHTML()).toBe('<p><span style="color: rgb(255, 0, 0);">a</span></p>');
    editor.destroy();
  });
});
