// The library picker portals its overlay to <body> and registers a capture-phase
// keydown listener on `document` — neither lives inside the editor shell. They
// must be disposed when the editor is destroyed (e.g. a destructive DOM swap
// removes the editor while the picker is open), or they leak: a stray modal over
// the page and a document listener whose closure pins the dead editor in memory.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { buildExtensions } from "../src/build-extensions";
import type { TipTapConfig } from "../src/default-config";
import { setEditorConfig } from "../src/editor-config";
import { openImagePicker } from "../src/image-picker";
import { Editor } from "../src/tiptap-runtime";

const ctx = { tiptap: {}, locale: "en", t: (k: string) => k };

function makeEditor(config: TipTapConfig): Editor {
  const element = document.createElement("div");
  document.body.appendChild(element);
  const editor = new Editor({ element, extensions: buildExtensions({}, ctx) });
  setEditorConfig(editor, config);
  return editor;
}

function overlay(): HTMLElement | null {
  return document.querySelector(".django-tiptap__modal-overlay");
}

beforeEach(() => {
  // Hold the picker in its loading state so the overlay stays up for the test.
  vi.stubGlobal(
    "fetch",
    vi.fn(() => new Promise<Response>(() => {})),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
});

describe("image picker lifecycle", () => {
  it("removes the body overlay when the editor is destroyed while open", () => {
    const editor = makeEditor({ imageListUrl: "/images/" });
    void openImagePicker(editor);
    expect(overlay()).not.toBeNull();

    editor.destroy();

    expect(overlay()).toBeNull();
  });

  it("removes the document keydown listener on teardown (no leak)", () => {
    const addSpy = vi.spyOn(document, "addEventListener");
    const removeSpy = vi.spyOn(document, "removeEventListener");
    const editor = makeEditor({ imageListUrl: "/images/" });
    void openImagePicker(editor);

    // The picker registered exactly one capture-phase keydown on `document`.
    const added = addSpy.mock.calls.filter((c) => c[0] === "keydown" && c[2] === true);
    expect(added).toHaveLength(1);
    const handler = added[0][1];

    editor.destroy();

    expect(removeSpy).toHaveBeenCalledWith("keydown", handler, true);
  });

  it("still closes normally via the close button (no double-teardown error)", () => {
    const editor = makeEditor({ imageListUrl: "/images/" });
    void openImagePicker(editor);

    const btn = document.querySelector(".django-tiptap__modal-close") as HTMLButtonElement;
    btn.click();
    expect(overlay()).toBeNull();

    // A later teardown of the editor must not throw or resurrect the overlay.
    editor.destroy();
    expect(overlay()).toBeNull();
  });
});
