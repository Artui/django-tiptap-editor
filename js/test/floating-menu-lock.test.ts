import { afterEach, describe, expect, it, vi } from "vitest";

import DjangoTipTap from "../src/index";
import type { Editor } from "../src/tiptap-runtime";

let seq = 0;

interface Field {
  textarea: HTMLTextAreaElement;
  editor: Editor;
  bubble: HTMLElement;
}

function mount(): Field {
  DjangoTipTap.ui.setRenderer("bubbleMenu", () => {
    const el = document.createElement("div");
    el.className = "my-bubble";
    return el;
  });
  const id = `bubble-${++seq}`;
  const host = document.createElement("div");
  host.innerHTML = `<textarea id="${id}">&lt;p&gt;Hello world&lt;/p&gt;</textarea>`;
  document.body.appendChild(host);
  const textarea = host.querySelector("textarea") as HTMLTextAreaElement;
  const editor = DjangoTipTap.init(textarea);
  // jsdom has no focus tracking and no layout: answer both for the menu's own checks.
  vi.spyOn(editor.view, "hasFocus").mockReturnValue(true);
  vi.spyOn(editor.view, "coordsAtPos").mockReturnValue({ left: 0, right: 0, top: 0, bottom: 0 });
  const bubble = document.querySelector(".my-bubble") as HTMLElement;
  return { textarea, editor, bubble };
}

const nextTick = (): Promise<void> => new Promise((resolve) => setTimeout(resolve, 0));

afterEach(() => {
  vi.restoreAllMocks();
  for (const textarea of document.querySelectorAll("textarea")) {
    DjangoTipTap.destroy(textarea.id);
  }
  document.body.innerHTML = "";
});

describe("a bubble menu across a lock", () => {
  it("hides when the field turns read-only and shows again when it unlocks", async () => {
    const { textarea, editor, bubble } = mount();
    editor.commands.setTextSelection({ from: 3, to: 6 });
    expect(bubble.style.display).toBe("");

    textarea.readOnly = true;
    await nextTick();
    expect(bubble.style.display).toBe("none");

    textarea.readOnly = false;
    await nextTick();
    expect(bubble.style.display).toBe("");
  });

  it("stops observing the lock once the editor is destroyed", async () => {
    const { textarea, editor } = mount();
    const dom = editor.view.dom as HTMLElement;
    DjangoTipTap.destroy(textarea.id);
    let reads = 0;
    Object.defineProperty(editor, "isEditable", {
      get: () => {
        reads += 1;
        return true;
      },
    });
    dom.setAttribute("contenteditable", "false");
    await nextTick();
    expect(reads).toBe(0);
  });
});
