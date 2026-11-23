// A locked field's editor takes no image from the clipboard, a drop or a resize handle:
// ProseMirror gates its own handlers on isEditable, and these routes are raw listeners.
import { afterEach, describe, expect, it, vi } from "vitest";

import DjangoTipTap from "../src/index";
import type { Editor } from "../src/tiptap-runtime";

const IMG = '<p><img src="https://i/x.png" width="200" height="100"></p>';
const FILE = new File(["x"], "x.png", { type: "image/png" });

let seq = 0;

interface Field {
  textarea: HTMLTextAreaElement;
  editor: Editor;
}

async function mount(attrs: string, body = "<p>a</p>"): Promise<Field> {
  const id = `locked-image-${++seq}`;
  const host = document.createElement("div");
  host.innerHTML = `<textarea id="${id}" ${attrs}></textarea>`;
  document.body.appendChild(host);
  const textarea = host.querySelector("textarea") as HTMLTextAreaElement;
  textarea.value = body;
  const editor = DjangoTipTap.init(textarea, { imageUploadUrl: "/upload/" });
  // The overlay is built in onCreate, a tick after construction.
  await new Promise((resolve) => setTimeout(resolve, 0));
  return { textarea, editor };
}

function stubUpload() {
  const fetchMock = vi.fn(async () => ({
    ok: true,
    json: async () => ({ location: "https://example.com/up.png" }),
  }));
  vi.stubGlobal("fetch", fetchMock);
  // jsdom has no layout: answer "nowhere" for ProseMirror's own drop handler.
  Object.defineProperty(document, "elementFromPoint", { value: () => null, configurable: true });
  return fetchMock;
}

function pasteFile(editor: Editor): void {
  const event = new Event("paste", { bubbles: true, cancelable: true });
  Object.defineProperty(event, "clipboardData", { value: { files: [FILE], getData: () => "" } });
  editor.view.dom.dispatchEvent(event);
}

function dropFile(editor: Editor): void {
  const event = new Event("drop", { bubbles: true, cancelable: true });
  Object.defineProperty(event, "dataTransfer", { value: { files: [FILE] } });
  editor.view.dom.dispatchEvent(event);
}

async function settle(): Promise<void> {
  for (let i = 0; i < 10; i++) {
    await Promise.resolve();
  }
}

// jsdom lays nothing out: give every <img> the rect its attributes imply.
function stubLayout(editor: Editor): void {
  Object.defineProperty(editor.view.dom, "clientWidth", { value: 800, configurable: true });
  vi.spyOn(HTMLImageElement.prototype, "getBoundingClientRect").mockImplementation(function (
    this: HTMLImageElement,
  ) {
    return {
      left: 0,
      top: 0,
      width: Number(this.getAttribute("width")) || 0,
      height: Number(this.getAttribute("height")) || 0,
    } as DOMRect;
  });
}

function overlay(): HTMLElement {
  return document.querySelector(".django-tiptap__img-overlay") as HTMLElement;
}

function dragSe(fromX: number, toX: number): void {
  const handle = document.querySelector(".django-tiptap__img-handle--se") as Element;
  handle.dispatchEvent(new MouseEvent("mousedown", { clientX: fromX, bubbles: true }));
  document.dispatchEvent(new MouseEvent("mousemove", { clientX: toX, bubbles: true }));
  document.dispatchEvent(new MouseEvent("mouseup", { clientX: toX, bubbles: true }));
}

function selectImage(editor: Editor): void {
  editor.commands.setNodeSelection(1);
}

async function nextTick(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 0));
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
});

describe("a pasted or dropped image file", () => {
  it("uploads and inserts on an editable field", async () => {
    const fetchMock = stubUpload();
    const { editor } = await mount("");
    pasteFile(editor);
    await settle();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(editor.getHTML()).toContain("<img");
  });

  it.each(["disabled", "readonly"])("is neither uploaded nor inserted on a %s field", async (attr) => {
    const fetchMock = stubUpload();
    const { editor } = await mount(attr);
    expect(editor.isEditable).toBe(false);
    pasteFile(editor);
    dropFile(editor);
    await settle();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(editor.getHTML()).toBe("<p>a</p>");
  });

  it("uploads again once the field is unlocked", async () => {
    const fetchMock = stubUpload();
    const { editor, textarea } = await mount("readonly");
    textarea.readOnly = false;
    await nextTick();
    expect(editor.isEditable).toBe(true);
    pasteFile(editor);
    await settle();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe("the image resize handles", () => {
  it("resize an image on an editable field", async () => {
    const { editor } = await mount("", IMG);
    stubLayout(editor);
    selectImage(editor);
    expect(overlay().hidden).toBe(false);
    dragSe(0, 100);
    expect(editor.getHTML()).toContain('width="300"');
  });

  it.each(["disabled", "readonly"])("are not shown on a %s field", async (attr) => {
    const { editor } = await mount(attr, IMG);
    stubLayout(editor);
    selectImage(editor);
    expect(overlay().hidden).toBe(true);
  });

  it("do nothing when dragged on a read-only field, even if shown", async () => {
    const { editor, textarea } = await mount("", IMG);
    stubLayout(editor);
    selectImage(editor);
    const before = editor.getHTML();
    textarea.readOnly = true;
    await nextTick();
    // Reach the handle past the hidden overlay, as a stale one would be.
    overlay().hidden = false;
    dragSe(0, -100);
    expect(editor.getHTML()).toBe(before);
    expect(editor.getHTML()).toContain('width="200"');
  });

  it("drop a drag begun before the field locked, committing nothing on mouseup", async () => {
    const { editor, textarea } = await mount("", IMG);
    stubLayout(editor);
    selectImage(editor);
    const before = editor.getHTML();
    const handle = document.querySelector(".django-tiptap__img-handle--se") as Element;
    handle.dispatchEvent(new MouseEvent("mousedown", { clientX: 0, bubbles: true }));
    document.dispatchEvent(new MouseEvent("mousemove", { clientX: 100, bubbles: true }));
    textarea.readOnly = true;
    await nextTick();
    document.dispatchEvent(new MouseEvent("mouseup", { clientX: 100, bubbles: true }));
    expect(editor.getHTML()).toBe(before);
    expect(overlay().hidden).toBe(true);
    expect((editor.view.nodeDOM(1) as HTMLElement).style.width).toBe("");
  });

  it("stop observing the lock once the editor is destroyed", async () => {
    const { editor, textarea } = await mount("", IMG);
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

  it("hide when the field locks and show again when it unlocks, with the image still selected", async () => {
    const { editor, textarea } = await mount("", IMG);
    stubLayout(editor);
    selectImage(editor);
    expect(overlay().hidden).toBe(false);

    textarea.disabled = true;
    await nextTick();
    expect(overlay().hidden).toBe(true);

    textarea.disabled = false;
    await nextTick();
    expect(overlay().hidden).toBe(false);
    dragSe(0, -100);
    expect(editor.getHTML()).toContain('width="100"');
  });
});
