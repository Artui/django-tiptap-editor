// The built-in `enterKey` config option: a high-priority keymap overriding
// StarterKit's Enter / Shift-Enter. Behavioural — builds a real editor,
// dispatches a keydown, and asserts the resulting HTML.
import { afterEach, describe, expect, it } from "vitest";

import { buildExtensions } from "../src/build-extensions";
import type { TipTapConfig } from "../src/default-config";
import { Editor } from "../src/tiptap-runtime";

const ctx = { tiptap: {}, locale: "en", t: (k: string) => k };

function makeEditor(config: TipTapConfig, content = "<p>ab</p>"): Editor {
  const element = document.createElement("div");
  document.body.appendChild(element);
  return new Editor({ element, content, extensions: buildExtensions(config, ctx) });
}

function pressEnter(editor: Editor, shift = false): void {
  editor.commands.focus("end");
  editor.view.dom.dispatchEvent(
    new KeyboardEvent("keydown", { key: "Enter", shiftKey: shift, bubbles: true, cancelable: true }),
  );
}

afterEach(() => {
  document.body.innerHTML = "";
});

describe("enterKey config", () => {
  it("defaults to a paragraph split (Enter starts a new <p>)", () => {
    const editor = makeEditor({});
    pressEnter(editor);
    expect(editor.getHTML()).toContain("</p><p>");
    editor.destroy();
  });

  it('"hardBreak" makes Enter insert a <br> instead of splitting', () => {
    const editor = makeEditor({ enterKey: "hardBreak" });
    pressEnter(editor);
    const html = editor.getHTML();
    expect(html).toContain("<br");
    expect(html).not.toContain("</p><p>");
    editor.destroy();
  });

  it('"swap" makes Enter a <br> and Shift-Enter a new paragraph', () => {
    const breakEditor = makeEditor({ enterKey: "swap" });
    pressEnter(breakEditor);
    expect(breakEditor.getHTML()).toContain("<br");
    breakEditor.destroy();

    const splitEditor = makeEditor({ enterKey: "swap" });
    pressEnter(splitEditor, true);
    expect(splitEditor.getHTML()).toContain("</p><p>");
    splitEditor.destroy();
  });
});

// Lists are structural: whatever the mode does to paragraphs, Enter in a list
// item starts the next item and Shift-Enter breaks the line inside it. A mode
// that inserted a <br> there left no way to add a bullet — or to leave the
// list — from the keyboard.
describe.each(["paragraph", "hardBreak", "swap"] as const)("enterKey %s, in a list", (mode) => {
  it("Enter starts the next list item", () => {
    const editor = makeEditor({ enterKey: mode }, "<ul><li><p>one</p></li></ul>");
    pressEnter(editor);
    editor.commands.insertContent("two");
    expect(editor.getHTML()).toBe("<ul><li><p>one</p></li><li><p>two</p></li></ul>");
    editor.destroy();
  });

  it("Enter starts the next item in an ordered list", () => {
    const editor = makeEditor({ enterKey: mode }, "<ol><li><p>one</p></li></ol>");
    pressEnter(editor);
    editor.commands.insertContent("two");
    expect(editor.getHTML()).toBe("<ol><li><p>one</p></li><li><p>two</p></li></ol>");
    editor.destroy();
  });

  it("Enter on an empty item leaves the list", () => {
    const editor = makeEditor({ enterKey: mode }, "<ul><li><p>one</p></li></ul>");
    pressEnter(editor);
    pressEnter(editor);
    editor.commands.insertContent("after");
    expect(editor.getHTML()).toBe("<ul><li><p>one</p></li></ul><p>after</p>");
    editor.destroy();
  });

  it("Shift-Enter breaks the line inside the item", () => {
    const editor = makeEditor({ enterKey: mode }, "<ul><li><p>one</p></li></ul>");
    pressEnter(editor, true);
    editor.commands.insertContent("two");
    expect(editor.getHTML()).toBe("<ul><li><p>one<br>two</p></li></ul>");
    editor.destroy();
  });
});
