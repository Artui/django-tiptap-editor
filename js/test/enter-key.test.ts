// The built-in `enterKey` config option: a high-priority keymap overriding
// StarterKit's Enter / Shift-Enter. Behavioural — builds a real editor,
// dispatches a keydown, and asserts the resulting HTML.
import { afterEach, describe, expect, it } from "vitest";

import { buildExtensions } from "../src/build-extensions";
import type { TipTapConfig } from "../src/default-config";
import { Editor } from "../src/tiptap-runtime";

const ctx = { tiptap: {}, locale: "en", t: (k: string) => k };

function makeEditor(config: TipTapConfig): Editor {
  const element = document.createElement("div");
  document.body.appendChild(element);
  return new Editor({ element, content: "<p>ab</p>", extensions: buildExtensions(config, ctx) });
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
