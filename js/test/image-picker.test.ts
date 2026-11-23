// The library picker portals its dialog to <body>, outside the editor shell. It must be
// disposed when the editor is destroyed (e.g. a destructive DOM swap removes the editor
// while the picker is open), and it keeps no `document` listener that would pin the editor.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { buildExtensions } from "../src/build-extensions";
import type { TipTapConfig } from "../src/default-config";
import { setEditorConfig } from "../src/editor-config";
import { openImagePicker } from "../src/image-picker";
import { Editor } from "../src/tiptap-runtime";
import { installDialog, removeDialog } from "./dialog-stub";

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
  installDialog();
  // Hold the picker in its loading state so the overlay stays up for the test.
  vi.stubGlobal(
    "fetch",
    vi.fn(() => new Promise<Response>(() => {})),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  removeDialog();
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

  it("adds no document keydown listener to leak past teardown", () => {
    const addSpy = vi.spyOn(document, "addEventListener");
    const editor = makeEditor({ imageListUrl: "/images/" });
    void openImagePicker(editor);

    expect(addSpy.mock.calls.filter((c) => c[0] === "keydown")).toHaveLength(0);

    editor.destroy();
    expect(overlay()).toBeNull();
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
