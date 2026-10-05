// Drag-to-resize on images. The size a document asks for, never the uploaded
// file — so every assertion here is about width/height attributes on the node.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { nextSize, withoutSizeDeclarations } from "../src/extensions/image-resize-overlay";

async function load() {
  const runtime = await import("../src/tiptap-runtime");
  const { buildExtensions } = await import("../src/build-extensions");
  return { runtime, buildExtensions };
}

type Loaded = Awaited<ReturnType<typeof load>>;

const IMG = '<p><img src="https://i/x.png" width="200" height="100"></p>';

// TipTap dispatches onCreate a tick after construction, and that is where the
// overlay is built -- so a test has to let that tick run before looking for it.
async function makeEditor(m: Loaded, config: Record<string, unknown> = {}, content = IMG) {
  const element = document.createElement("div");
  element.className = "django-tiptap__content";
  document.body.appendChild(element);
  const editor = new m.runtime.Editor({
    element,
    content,
    extensions: m.buildExtensions(config, { tiptap: {}, locale: "en", t: (k: string) => k }),
  });
  await new Promise((resolve) => setTimeout(resolve, 0));
  return editor;
}

// The image node's own element, as ProseMirror rendered it -- the element the
// overlay measures. Not `querySelector("img")`: prosemirror-view puts a
// zero-size `img.ProseMirror-separator` in front of an inline atom that opens a
// block or follows another atom, with no browser check, so in jsdom as in any
// browser the first <img> in the editor is that separator rather than the image.
function imageDOM(editor: { view: { nodeDOM: (pos: number) => unknown } }): HTMLElement {
  return editor.view.nodeDOM(1) as HTMLElement;
}

// jsdom lays nothing out, so the overlay would read a zero-sized image. Give
// every <img> the rect its attributes imply, and the editor a width for the
// clamp. On the prototype rather than on one element, because picking the
// element is exactly what the separator above gets wrong, and a redraw would
// hand the overlay a fresh element anyway; the separator carries no
// width/height attributes, so it measures zero, as it does in a browser.
// afterEach's restoreAllMocks takes the spy down.
function stubLayout(editor: { view: { dom: HTMLElement } }, width: number): void {
  Object.defineProperty(editor.view.dom, "clientWidth", { value: width, configurable: true });
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

// Select the image so the overlay shows its handles, the way a click does.
function selectImage(editor: { commands: { setNodeSelection: (pos: number) => void } }): void {
  editor.commands.setNodeSelection(1);
}

function handle(corner: string): Element {
  const el = document.querySelector(`.django-tiptap__img-handle--${corner}`);
  if (!el) {
    throw new Error(`no ${corner} handle`);
  }
  return el;
}

function drag(handle: Element, fromX: number, toX: number): void {
  handle.dispatchEvent(new MouseEvent("mousedown", { clientX: fromX, bubbles: true }));
  document.dispatchEvent(new MouseEvent("mousemove", { clientX: toX, bubbles: true }));
  document.dispatchEvent(new MouseEvent("mouseup", { clientX: toX, bubbles: true }));
}

beforeEach(() => {
  vi.resetModules();
});

afterEach(() => {
  vi.restoreAllMocks();
  document.body.innerHTML = "";
});

describe("nextSize", () => {
  it("keeps the aspect ratio and follows the pointer", () => {
    expect(nextSize({ width: 200, height: 100 }, 50, "se", 1000)).toEqual({
      width: 250,
      height: 125,
    });
  });

  it("inverts the delta for west handles", () => {
    expect(nextSize({ width: 200, height: 100 }, -50, "sw", 1000)).toEqual({
      width: 250,
      height: 125,
    });
  });

  it("clamps to the minimum and to the editor width", () => {
    expect(nextSize({ width: 200, height: 100 }, -500, "se", 1000).width).toBe(24);
    expect(nextSize({ width: 200, height: 100 }, 5000, "se", 600).width).toBe(600);
  });

  it("treats a non-positive max as unconstrained", () => {
    // A hidden or not-yet-laid-out editor reports zero width; clamping to that
    // would collapse every image to the minimum.
    expect(nextSize({ width: 200, height: 100 }, 300, "se", 0).width).toBe(500);
  });

  it("survives a zero-width start without producing NaN", () => {
    expect(nextSize({ width: 0, height: 0 }, 100, "se", 1000)).toEqual({
      width: 100,
      height: 100,
    });
  });
});

describe("withoutSizeDeclarations", () => {
  it("drops sizing declarations but keeps layout ones", () => {
    expect(withoutSizeDeclarations("float: right; margin: 8px; width: 500px")).toBe(
      "float: right; margin: 8px;",
    );
  });

  it("returns null when nothing survives, and for a missing style", () => {
    expect(withoutSizeDeclarations("width: 500px; height: 200px")).toBeNull();
    expect(withoutSizeDeclarations(null)).toBeNull();
  });
});

describe("resize overlay", () => {
  it("leaves the image node's own DOM untouched", async () => {
    const m = await load();
    const editor = await makeEditor(m);

    // No wrapper around the image: that is what keeps the caret beside it the
    // same as it is with resizing off.
    // nodeDOM is the node's outermost element, so a wrapper would show up here
    // as its tag, while still sitting in the paragraph.
    const img = imageDOM(editor);
    expect(img.tagName).toBe("IMG");
    expect(img.parentElement?.tagName).toBe("P");
    expect(editor.view.dom.querySelector(".django-tiptap__img")).toBeNull();

    editor.destroy();
  });

  it("shows four handles only while the image is selected", async () => {
    const m = await load();
    const editor = await makeEditor(m);
    stubLayout(editor, 800);

    const overlay = document.querySelector(".django-tiptap__img-overlay");
    expect(overlay).not.toBeNull();
    expect((overlay as HTMLElement).hidden).toBe(true);

    selectImage(editor);
    expect((overlay as HTMLElement).hidden).toBe(false);
    expect(overlay?.querySelectorAll(".django-tiptap__img-handle")).toHaveLength(4);

    editor.commands.setTextSelection(0);
    expect((overlay as HTMLElement).hidden).toBe(true);

    editor.destroy();
  });

  it("adds no overlay at all when imageResize is false", async () => {
    const m = await load();
    const editor = await makeEditor(m, { imageResize: false });
    stubLayout(editor, 800);
    selectImage(editor);

    expect(document.querySelector(".django-tiptap__img-overlay")).toBeNull();
    expect(imageDOM(editor).tagName).toBe("IMG");

    editor.destroy();
  });

  it("tracks the selected image's box", async () => {
    const m = await load();
    const editor = await makeEditor(m);
    stubLayout(editor, 800);
    selectImage(editor);

    // The fixture is only a test of *which* element gets measured while the
    // first <img> in the editor is something else: here, the separator
    // ProseMirror puts in front of an image that opens its paragraph.
    expect(editor.view.dom.querySelector("img")).not.toBe(imageDOM(editor));
    // View-only: the separator is not a node, so saved content never sees it.
    expect(editor.getHTML()).not.toContain("ProseMirror-separator");

    const overlay = document.querySelector(".django-tiptap__img-overlay") as HTMLElement;
    expect(overlay.style.width).toBe("200px");
    expect(overlay.style.height).toBe("100px");

    editor.destroy();
  });

  it("writes the dragged size to the node's width/height attributes", async () => {
    const m = await load();
    const editor = await makeEditor(m);
    stubLayout(editor, 800);
    selectImage(editor);

    drag(handle("se"), 0, 100);

    expect(editor.getHTML()).toContain('width="300"');
    expect(editor.getHTML()).toContain('height="150"');

    editor.destroy();
  });

  it("leaves the uploaded file's own address untouched", async () => {
    const m = await load();
    const editor = await makeEditor(m);
    stubLayout(editor, 800);
    selectImage(editor);

    drag(handle("se"), 0, 100);

    // Display size only: nothing about the asset itself changes.
    expect(editor.getHTML()).toContain('src="https://i/x.png"');

    editor.destroy();
  });

  it("leaves the image selected after a drag, not the caret in front of it", async () => {
    const m = await load();
    const editor = await makeEditor(m);
    stubLayout(editor, 800);
    selectImage(editor);

    drag(handle("se"), 0, 100);

    // setNodeMarkup maps a node selection to a text position before the node,
    // which drops the caret in front of the image and takes the handles away
    // with it. The image has to still be the selection afterwards.
    const selection = editor.state.selection as unknown as { node?: { type: { name: string } } };
    expect(selection.node?.type.name).toBe("image");
    expect((document.querySelector(".django-tiptap__img-overlay") as HTMLElement).hidden).toBe(
      false,
    );

    editor.destroy();
  });

  it("clears the drag preview off the image once committed", async () => {
    const m = await load();
    const editor = await makeEditor(m);
    stubLayout(editor, 800);
    selectImage(editor);

    drag(handle("se"), 0, 100);

    const img = imageDOM(editor);
    expect(img.style.width).toBe("");
    expect(img.style.height).toBe("");

    editor.destroy();
  });

  it("clears a style width that would outrank the resized attribute", async () => {
    const m = await load();
    const editor = await makeEditor(
      m,
      {},
      '<p><img src="https://i/x.png" width="200" height="100" style="float: right; width: 500px"></p>',
    );
    stubLayout(editor, 800);
    selectImage(editor);

    drag(handle("se"), 0, 100);

    const html = editor.getHTML();
    expect(html).toContain('width="300"');
    expect(html).toContain("float: right");
    expect(html).not.toContain("width: 500px");

    editor.destroy();
  });

  it("produces one undo step for a whole drag", async () => {
    const m = await load();
    const editor = await makeEditor(m);
    stubLayout(editor, 800);
    selectImage(editor);

    handle("se").dispatchEvent(new MouseEvent("mousedown", { clientX: 0, bubbles: true }));
    for (const x of [20, 40, 60, 80, 100]) {
      document.dispatchEvent(new MouseEvent("mousemove", { clientX: x, bubbles: true }));
    }
    document.dispatchEvent(new MouseEvent("mouseup", { clientX: 100, bubbles: true }));

    expect(editor.getHTML()).toContain('width="300"');
    editor.commands.undo();
    expect(editor.getHTML()).toContain('width="200"');

    editor.destroy();
  });

  it("stops listening once the drag ends", async () => {
    const m = await load();
    const editor = await makeEditor(m);
    stubLayout(editor, 800);
    selectImage(editor);

    drag(handle("se"), 0, 100);
    // A stray move/release after the drag must not keep resizing. Both events
    // are needed to make this falsifiable: a leaked mousemove listener alone
    // never commits, so only a second mouseup would show the leak.
    document.dispatchEvent(new MouseEvent("mousemove", { clientX: 400, bubbles: true }));
    document.dispatchEvent(new MouseEvent("mouseup", { clientX: 400, bubbles: true }));

    expect(editor.getHTML()).toContain('width="300"');
    expect(editor.getHTML()).not.toContain('width="600"');

    editor.destroy();
  });

  it("takes the overlay down with the editor", async () => {
    const m = await load();
    const editor = await makeEditor(m);
    stubLayout(editor, 800);
    selectImage(editor);
    expect(document.querySelector(".django-tiptap__img-overlay")).not.toBeNull();

    editor.destroy();

    expect(document.querySelector(".django-tiptap__img-overlay")).toBeNull();
  });
});
