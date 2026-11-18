import { afterEach, describe, expect, it, vi } from "vitest";

import { buildExtensions } from "../src/build-extensions";
import { DEFAULT_TOOLBAR } from "../src/default-config";
import type { TipTapConfig } from "../src/default-config";
import { setEditorConfig } from "../src/editor-config";
import { getTranslator, setTranslator } from "../src/i18n";
import { rendererContext } from "../src/renderers";
import { registerButton } from "../src/toolbar/button-registry";
import { registerBuiltInButtons } from "../src/toolbar/built-in-buttons";
import { renderToolbar } from "../src/toolbar/render-toolbar";
import type { RenderedToolbar } from "../src/toolbar/render-toolbar";
import { Editor } from "../src/tiptap-runtime";

const ctx = { tiptap: {}, locale: "en", t: (k: string) => k };

function mount(extra: Record<string, unknown> = {}, toolbar?: string[][]): { editor: Editor; bar: RenderedToolbar } {
  registerBuiltInButtons();
  registerButton("stamp", { title: "Stamp", icon: "<svg></svg>", onClick: () => undefined });
  const config = { toolbar: toolbar ?? EVERYTHING, ...extra } as TipTapConfig;
  const element = document.createElement("div");
  document.body.appendChild(element);
  const editor = new Editor({ element, content: "<p>ab</p>", extensions: buildExtensions(config, ctx) });
  setEditorConfig(editor, config);
  setTranslator(editor, getTranslator("en"));
  const bar = renderToolbar(editor, config);
  document.body.appendChild(bar.el);
  editor.on("transaction", () => bar.refresh());
  bar.refresh();
  return { editor, bar };
}

function btn(bar: RenderedToolbar, key: string): HTMLButtonElement {
  const el = bar.el.querySelector<HTMLButtonElement>(
    `[data-key="${key}"]:is(button), [data-key="${key}"] .django-tiptap__dropdown-trigger`,
  );
  if (!el) {
    throw new Error(`no ${key} in the toolbar`);
  }
  return el;
}

function snapshot(bar: RenderedToolbar): Array<[string | null, string, string, string | null]> {
  return Array.from(bar.el.querySelectorAll<HTMLButtonElement>("button")).map((b) => [
    b.closest("[data-key]")?.getAttribute("data-key") ?? null,
    b.innerHTML,
    b.title,
    b.getAttribute("aria-label"),
  ]);
}

const EVERYTHING = [...DEFAULT_TOOLBAR, ["horizontalRule", "mergeTags", "stamp"]];
const DROPDOWNS = ["fontSize", "fontFamily", "color", "highlight", "image", "mergeTags", "table"];

afterEach(() => {
  document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
  vi.restoreAllMocks();
  document.body.innerHTML = "";
});

describe("toolbarLabels", () => {
  it("renders a label as literal text, never markup", () => {
    const { bar } = mount({ toolbarLabels: { mergeTags: "<b>x</b>" } });
    const trigger = btn(bar, "mergeTags");
    expect(trigger.querySelector("b")).toBeNull();
    expect(trigger.querySelector(".django-tiptap__btn-label")?.textContent).toBe("<b>x</b>");
    expect(trigger.title).toBe("<b>x</b>");
    expect(trigger.getAttribute("aria-label")).toBe("<b>x</b>");
  });

  it.each([
    ["mergeTags", "Insert token"],
    ["bold", "Strong"],
    ["stamp", "Stamp it"],
  ])("labels %s after its glyph, with title and aria-label equal to it", (key, label) => {
    const { bar } = mount({ toolbarLabels: { [key]: label } }, EVERYTHING);
    const button = btn(bar, key);
    const span = button.querySelector(".django-tiptap__btn-label");
    expect(span?.textContent).toBe(label);
    expect(button.title).toBe(label);
    expect(button.getAttribute("aria-label")).toBe(label);
    const children = Array.from(button.children);
    expect(children.indexOf(span as Element)).toBeGreaterThan(0);
    const caret = button.querySelector(".django-tiptap__caret");
    if (caret) {
      expect(children.at(-1)).toBe(caret);
    } else {
      expect(children.at(-1)).toBe(span);
    }
  });

  it.each(DROPDOWNS)("puts the label between the glyph and the caret on the %s trigger", (key) => {
    const { bar } = mount({ toolbarLabels: { [key]: "L" } });
    const trigger = btn(bar, key);
    const span = trigger.querySelector(".django-tiptap__btn-label") as Element;
    expect(span.nextElementSibling?.classList.contains("django-tiptap__caret")).toBe(true);
    expect(trigger.getAttribute("aria-label")).toBe("L");
  });

  it("leaves every button as it was without the key, with {} and with empty labels", () => {
    const base = snapshot(mount({}, EVERYTHING).bar);
    document.body.innerHTML = "";
    expect(snapshot(mount({ toolbarLabels: {} }, EVERYTHING).bar)).toEqual(base);
    document.body.innerHTML = "";
    const empty = Object.fromEntries(EVERYTHING.flat().map((k) => [k, ""]));
    expect(snapshot(mount({ toolbarLabels: empty }, EVERYTHING).bar)).toEqual(base);
    expect(document.querySelector(".django-tiptap__btn-label")).toBeNull();
  });

  it("replaces the font-size readout, and the value no longer renames the trigger", () => {
    const { editor, bar } = mount({ toolbarLabels: { fontSize: "Size" } });
    const trigger = btn(bar, "fontSize");
    expect(trigger.querySelector(".django-tiptap__value")).toBeNull();
    editor.chain().selectAll().setMark("textStyle", { fontSize: "24px" }).run();
    expect(trigger.getAttribute("aria-label")).toBe("Size");
    expect(trigger.textContent).not.toContain("24");
  });

  it("keeps aria-pressed and aria-expanded on labelled controls", () => {
    const { editor, bar } = mount({ toolbarLabels: { bold: "Strong", table: "Grid" } });
    editor.chain().selectAll().toggleBold().run();
    expect(btn(bar, "bold").getAttribute("aria-pressed")).toBe("true");
    const table = btn(bar, "table");
    expect(table.getAttribute("aria-expanded")).toBe("false");
    table.click();
    expect(table.getAttribute("aria-expanded")).toBe("true");
  });

  it("is inert, with no warning, for an absent, unknown or feature-hidden button", () => {
    const warn = vi.spyOn(console, "warn");
    const error = vi.spyOn(console, "error");
    const { bar } = mount(
      { features: ["bold"], toolbarLabels: { italic: "I", nope: "N", stamp: "S" } },
      [["bold", "italic"]],
    );
    expect(bar.el.querySelector(".django-tiptap__btn-label")).toBeNull();
    expect(error).not.toHaveBeenCalled();
    expect(warn.mock.calls.flat().join(" ")).not.toMatch(/label/i);
  });

  it("reaches a custom region that renders a spec through getButton", () => {
    registerBuiltInButtons();
    const config = { toolbarLabels: { mergeTags: "Insert token" } } as TipTapConfig;
    const element = document.createElement("div");
    const editor = new Editor({ element, content: "<p>a</p>", extensions: buildExtensions(config, ctx) });
    setEditorConfig(editor, config);
    const region = rendererContext(editor, config, getTranslator("en"));
    const control = region.getButton("mergeTags")?.render?.(editor);
    const trigger = control?.el.querySelector(".django-tiptap__dropdown-trigger");
    expect(trigger?.querySelector(".django-tiptap__btn-label")?.textContent).toBe("Insert token");
    expect(trigger?.getAttribute("aria-label")).toBe("Insert token");
  });
});
