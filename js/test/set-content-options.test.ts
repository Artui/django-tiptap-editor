// Tiptap 3's setContent takes an options object, and docs/extending.md tells
// custom-extension authors what the Tiptap 2 boolean spelling now does. These
// hold that note to the editor: an options object controls the update, and a
// bare boolean is read as an empty options object, so `false` still emits one.
import { describe, expect, it } from "vitest";

import { buildExtensions } from "../src/build-extensions";
import { Editor } from "../src/tiptap-runtime";

function updatesFrom(set: (editor: Editor) => void): number {
  const editor = new Editor({
    element: document.createElement("div"),
    content: "<p>a</p>",
    extensions: buildExtensions({}, { tiptap: {}, locale: "en", t: (k) => k }),
  });
  let updates = 0;
  editor.on("update", () => {
    updates += 1;
  });
  set(editor);
  editor.destroy();
  return updates;
}

describe("setContent options", () => {
  it("emits no update when asked not to", () => {
    expect(updatesFrom((e) => e.commands.setContent("<p>b</p>", { emitUpdate: false }))).toBe(0);
  });

  it("emits an update for the Tiptap 2 boolean spelling, false included", () => {
    // The cast is the point: TypeScript rejects the boolean, a plain <script> does not.
    const legacy = false as unknown as { emitUpdate?: boolean };
    expect(updatesFrom((e) => e.commands.setContent("<p>b</p>", legacy))).toBe(1);
  });
});
