// Drag-to-resize on images. The size a document asks for, never the uploaded
// file — so every assertion here is about width/height attributes on the node.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { nextSize, withoutSizeDeclarations } from "../src/extensions/image-resize-view";

async function load() {
  const runtime = await import("../src/tiptap-runtime");
  const { buildExtensions } = await import("../src/build-extensions");
  return { runtime, buildExtensions };
}

type Loaded = Awaited<ReturnType<typeof load>>;

const IMG = '<p><img src="https://i/x.png" width="200" height="100"></p>';

function makeEditor(m: Loaded, config: Record<string, unknown> = {}, content = IMG) {
  const element = document.createElement("div");
  element.className = "django-tiptap__content";
  document.body.appendChild(element);
  return new m.runtime.Editor({
    element,
    content,
    extensions: m.buildExtensions(config, { tiptap: {}, locale: "en", t: (k: string) => k }),
  });
}

// jsdom lays nothing out, so the drag start size comes from the width/height
// attributes; stub the editor width to give the clamp something to work with.
function stubWidth(editor: { view: { dom: HTMLElement } }, width: number): void {
  Object.defineProperty(editor.view.dom, "clientWidth", { value: width, configurable: true });
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

describe("resize handles", () => {
  it("renders four handles around the image by default", async () => {
    const m = await load();
    const editor = makeEditor(m);

    const wrapper = editor.view.dom.querySelector(".django-tiptap__img");
    expect(wrapper).not.toBeNull();
    expect(wrapper?.querySelectorAll(".django-tiptap__img-handle")).toHaveLength(4);
    expect(wrapper?.querySelector("img")?.getAttribute("src")).toBe("https://i/x.png");

    editor.destroy();
  });

  it("is dropped entirely when imageResize is false", async () => {
    const m = await load();
    const editor = makeEditor(m, { imageResize: false });

    expect(editor.view.dom.querySelector(".django-tiptap__img")).toBeNull();
    expect(editor.view.dom.querySelector("img")).not.toBeNull();

    editor.destroy();
  });

  it("writes the dragged size to the node's width/height attributes", async () => {
    const m = await load();
    const editor = makeEditor(m);
    stubWidth(editor, 800);

    const handle = editor.view.dom.querySelector(".django-tiptap__img-handle--se")!;
    drag(handle, 0, 100);

    expect(editor.getHTML()).toContain('width="300"');
    expect(editor.getHTML()).toContain('height="150"');

    editor.destroy();
  });

  it("leaves the uploaded file's own address untouched", async () => {
    const m = await load();
    const editor = makeEditor(m);
    stubWidth(editor, 800);

    drag(editor.view.dom.querySelector(".django-tiptap__img-handle--se")!, 0, 100);

    // Display size only: nothing about the asset itself changes.
    expect(editor.getHTML()).toContain('src="https://i/x.png"');

    editor.destroy();
  });

  it("clears a style width that would outrank the resized attribute", async () => {
    const m = await load();
    const editor = makeEditor(
      m,
      {},
      '<p><img src="https://i/x.png" width="200" height="100" style="float: right; width: 500px"></p>',
    );
    stubWidth(editor, 800);

    drag(editor.view.dom.querySelector(".django-tiptap__img-handle--se")!, 0, 100);

    const html = editor.getHTML();
    expect(html).toContain('width="300"');
    expect(html).toContain("float: right");
    expect(html).not.toContain("width: 500px");

    editor.destroy();
  });

  it("produces one undo step for a whole drag", async () => {
    const m = await load();
    const editor = makeEditor(m);
    stubWidth(editor, 800);

    const handle = editor.view.dom.querySelector(".django-tiptap__img-handle--se")!;
    handle.dispatchEvent(new MouseEvent("mousedown", { clientX: 0, bubbles: true }));
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
    const editor = makeEditor(m);
    stubWidth(editor, 800);

    drag(editor.view.dom.querySelector(".django-tiptap__img-handle--se")!, 0, 100);
    // A stray move/release after the drag must not keep resizing. Both events
    // are needed to make this falsifiable: a leaked mousemove listener alone
    // never commits, so only a second mouseup would show the leak.
    document.dispatchEvent(new MouseEvent("mousemove", { clientX: 400, bubbles: true }));
    document.dispatchEvent(new MouseEvent("mouseup", { clientX: 400, bubbles: true }));

    expect(editor.getHTML()).toContain('width="300"');
    expect(editor.getHTML()).not.toContain('width="600"');

    editor.destroy();
  });
});
