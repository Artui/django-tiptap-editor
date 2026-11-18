import { afterEach, describe, expect, it, vi } from "vitest";

import { buildExtensions } from "../src/build-extensions";
import type { TipTapConfig } from "../src/default-config";
import { setEditorConfig } from "../src/editor-config";
import { getTranslator, setTranslator } from "../src/i18n";
import { registerBuiltInButtons } from "../src/toolbar/built-in-buttons";
import { renderToolbar } from "../src/toolbar/render-toolbar";
import { Editor } from "../src/tiptap-runtime";

const ctx = { tiptap: {}, locale: "en", t: (k: string) => k };

function makeEditor(config: TipTapConfig, locale = "en"): Editor {
  const element = document.createElement("div");
  document.body.appendChild(element);
  const editor = new Editor({ element, content: "<p>ab</p>", extensions: buildExtensions(config, ctx) });
  setEditorConfig(editor, config);
  setTranslator(editor, getTranslator(locale));
  return editor;
}

afterEach(() => {
  vi.restoreAllMocks();
  document.body.innerHTML = "";
});

describe("the horizontalRule toolbar button", () => {
  it("renders and inserts an hr on click", () => {
    registerBuiltInButtons();
    const config: TipTapConfig = { toolbar: [["horizontalRule"]] };
    const editor = makeEditor(config);
    const toolbar = renderToolbar(editor, config);
    const button = toolbar.el.querySelector<HTMLButtonElement>('[data-key="horizontalRule"]');
    expect(button).not.toBeNull();
    expect(button?.hasAttribute("aria-pressed")).toBe(false);
    button?.click();
    expect(editor.getHTML()).toContain("<hr>");
  });

  it("is hidden with one warning when features leave horizontalRule out", () => {
    registerBuiltInButtons();
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const config: TipTapConfig = { features: ["bold"], toolbar: [["horizontalRule"]] };
    const editor = makeEditor(config);
    const toolbar = renderToolbar(editor, config);
    expect(toolbar.el.querySelector('[data-key="horizontalRule"]')).toBeNull();
    expect(warn).toHaveBeenCalledTimes(1);
    expect(String(warn.mock.calls[0][0])).toContain("horizontalRule");
  });

  it.each([
    ["en", "Horizontal rule"],
    ["sv", "Vågrät linje"],
  ])("is titled in %s", (locale, title) => {
    registerBuiltInButtons();
    const config: TipTapConfig = { toolbar: [["horizontalRule"]] };
    const editor = makeEditor(config, locale);
    const button = renderToolbar(editor, config).el.querySelector<HTMLButtonElement>('[data-key="horizontalRule"]');
    expect(button?.title).toBe(title);
  });
});
