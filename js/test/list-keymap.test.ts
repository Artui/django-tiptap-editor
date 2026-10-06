// ListKeymap is on in the baseline. It ships in StarterKit 3 and changes only
// what Backspace and Delete do at the edges of a list item; it adds no schema
// and no markup. These pin the behaviour the CHANGELOG describes, so turning it
// back off (or an upgrade changing it) fails here rather than in a user's list.
import { afterEach, describe, expect, it } from "vitest";

import { buildExtensions } from "../src/build-extensions";
import { Editor } from "../src/tiptap-runtime";

const ctx = { tiptap: {}, locale: "en", t: (k: string) => k };
const TWO_ITEMS = "<ul><li><p>a</p></li><li><p>b</p></li></ul>";

function makeEditor(): Editor {
  const element = document.createElement("div");
  document.body.appendChild(element);
  return new Editor({ element, content: TWO_ITEMS, extensions: buildExtensions({}, ctx) });
}

// Position of the first character of `text`, or just past its last.
function positionOf(editor: Editor, text: string, end = false): number {
  let found = -1;
  editor.state.doc.descendants((node, pos) => {
    if (found < 0 && node.isText && node.text === text) {
      found = end ? pos + text.length : pos;
    }
    return found < 0;
  });
  return found;
}

function press(editor: Editor, key: "Backspace" | "Delete", at: number): void {
  editor.commands.setTextSelection(at);
  editor.view.dom.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true }));
}

afterEach(() => {
  document.body.innerHTML = "";
});

describe("list keymap", () => {
  // Without ListKeymap, both keys below instead move the item's paragraph into
  // the item before it: <ul><li><p>a</p><p>b</p></li></ul>.
  it("Backspace at the start of the last item lifts it out of the list", () => {
    const editor = makeEditor();
    press(editor, "Backspace", positionOf(editor, "b"));
    expect(editor.getHTML()).toBe("<ul><li><p>a</p></li></ul><p>b</p>");
    editor.destroy();
  });

  it("Delete at the end of an item joins the next item onto it", () => {
    const editor = makeEditor();
    press(editor, "Delete", positionOf(editor, "a", true));
    expect(editor.getHTML()).toBe("<ul><li><p>ab</p></li></ul>");
    editor.destroy();
  });
});
