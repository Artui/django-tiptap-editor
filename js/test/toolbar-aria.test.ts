import { afterEach, describe, expect, it, vi } from "vitest";

import { buildExtensions } from "../src/build-extensions";
import type { TipTapConfig } from "../src/default-config";
import { setEditorConfig } from "../src/editor-config";
import { getTranslator, registerLocale, setTranslator } from "../src/i18n";
import { registerButton } from "../src/toolbar/button-registry";
import { registerBuiltInButtons } from "../src/toolbar/built-in-buttons";
import { renderToolbar } from "../src/toolbar/render-toolbar";
import type { RenderedToolbar } from "../src/toolbar/render-toolbar";
import { Editor } from "../src/tiptap-runtime";

const ctx = { tiptap: {}, locale: "en", t: (k: string) => k };

function mount(
  toolbar: string[][],
  content: string,
  locale = "en",
  extra: Partial<TipTapConfig> = {},
): { editor: Editor; bar: RenderedToolbar } {
  registerBuiltInButtons();
  const config: TipTapConfig = { toolbar, ...extra };
  const element = document.createElement("div");
  document.body.appendChild(element);
  const editor = new Editor({ element, content, extensions: buildExtensions(config, ctx) });
  setEditorConfig(editor, config);
  setTranslator(editor, getTranslator(locale));
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

function triggers(bar: RenderedToolbar): HTMLButtonElement[] {
  return Array.from(bar.el.querySelectorAll<HTMLButtonElement>(".django-tiptap__dropdown-trigger"));
}

function closeAll(bar: RenderedToolbar): void {
  document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
  for (const trigger of triggers(bar)) {
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
  }
}

let mounted: RenderedToolbar | null = null;

afterEach(() => {
  if (mounted) {
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    mounted = null;
  }
  vi.restoreAllMocks();
  document.body.innerHTML = "";
});

describe("aria-pressed on toggle buttons", () => {
  it("follows is-active as the caret enters and leaves bold", () => {
    const { editor, bar } = mount([["bold", "italic"]], "<p><strong>ab</strong>cd</p>");
    editor.commands.setTextSelection(2);
    expect(btn(bar, "bold").classList.contains("is-active")).toBe(true);
    expect(btn(bar, "bold").getAttribute("aria-pressed")).toBe("true");
    expect(btn(bar, "italic").getAttribute("aria-pressed")).toBe("false");
    editor.commands.setTextSelection(5);
    expect(btn(bar, "bold").classList.contains("is-active")).toBe(false);
    expect(btn(bar, "bold").getAttribute("aria-pressed")).toBe("false");
  });

  it.each(["undo", "redo", "unlink", "clearFormatting"])(
    "leaves %s, which has no isActive, without aria-pressed",
    (key) => {
      const { bar } = mount([[key]], "<p>ab</p>");
      expect(btn(bar, key).hasAttribute("aria-pressed")).toBe(false);
    },
  );

  it("applies to link, which has isActive", () => {
    const { editor, bar } = mount([["link"]], '<p><a href="https://x.test">ab</a>cd</p>');
    editor.commands.setTextSelection(2);
    expect(btn(bar, "link").getAttribute("aria-pressed")).toBe("true");
  });

  it("applies to a registered spec with isActive and not to one without", () => {
    let on = false;
    registerButton("ariaToggle", { icon: "T", title: "t", isActive: () => on, onClick: () => {} });
    registerButton("ariaAction", { icon: "A", title: "a", onClick: () => {} });
    const { bar } = mount([["ariaToggle", "ariaAction"]], "<p>ab</p>");
    expect(btn(bar, "ariaToggle").getAttribute("aria-pressed")).toBe("false");
    on = true;
    bar.refresh();
    expect(btn(bar, "ariaToggle").getAttribute("aria-pressed")).toBe("true");
    expect(btn(bar, "ariaAction").hasAttribute("aria-pressed")).toBe(false);
  });

  it("flips sourceView after its click, which fires no transaction", () => {
    const { bar } = mount([["sourceView"]], "<p>ab</p>");
    expect(btn(bar, "sourceView").getAttribute("aria-pressed")).toBe("false");
    btn(bar, "sourceView").click();
    expect(btn(bar, "sourceView").getAttribute("aria-pressed")).toBe("true");
  });
});

describe("aria-expanded on dropdown triggers", () => {
  const ALL = [["fontSize", "fontFamily", "color", "highlight", "image", "mergeTags", "table"]];

  it("is false on every trigger at render", () => {
    const { bar } = mount(ALL, "<p>ab</p>", "en", { mergeTags: [{ label: "N", value: "{{ n }}" }] });
    mounted = bar;
    expect(triggers(bar)).toHaveLength(7);
    for (const trigger of triggers(bar)) {
      expect(trigger.getAttribute("aria-expanded")).toBe("false");
    }
  });

  it("is true when opened and false after Escape", () => {
    const { bar } = mount(ALL, "<p>ab</p>", "en", { mergeTags: [{ label: "N", value: "{{ n }}" }] });
    mounted = bar;
    for (const trigger of triggers(bar)) {
      trigger.click();
      expect(trigger.getAttribute("aria-expanded")).toBe("true");
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
      expect(trigger.getAttribute("aria-expanded")).toBe("false");
    }
  });

  it("is false after an outside mousedown", () => {
    const { bar } = mount([["fontSize"]], "<p>ab</p>");
    mounted = bar;
    btn(bar, "fontSize").click();
    expect(btn(bar, "fontSize").getAttribute("aria-expanded")).toBe("true");
    document.body.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    expect(btn(bar, "fontSize").getAttribute("aria-expanded")).toBe("false");
  });

  it("is false after an item is picked", () => {
    const { bar } = mount([["fontSize"]], "<p>ab</p>");
    mounted = bar;
    btn(bar, "fontSize").click();
    bar.el.querySelector<HTMLButtonElement>(".django-tiptap__menu-item")?.click();
    expect(btn(bar, "fontSize").getAttribute("aria-expanded")).toBe("false");
  });

  it("is false on the first when a second dropdown opens", () => {
    const { bar } = mount([["fontSize", "fontFamily"]], "<p>ab</p>");
    mounted = bar;
    btn(bar, "fontSize").click();
    btn(bar, "fontFamily").click();
    expect(btn(bar, "fontSize").getAttribute("aria-expanded")).toBe("false");
    expect(btn(bar, "fontFamily").getAttribute("aria-expanded")).toBe("true");
    closeAll(bar);
  });

  it("is false after the trigger is clicked again", () => {
    const { bar } = mount([["fontSize"]], "<p>ab</p>");
    mounted = bar;
    btn(bar, "fontSize").click();
    btn(bar, "fontSize").click();
    expect(btn(bar, "fontSize").getAttribute("aria-expanded")).toBe("false");
  });
});

function valueText(bar: RenderedToolbar): string | null | undefined {
  return btn(bar, "fontSize").querySelector(".django-tiptap__value-text")?.textContent;
}

describe("the font-size trigger shows the current size", () => {
  it.each([
    ["en", "Default", "Font size: Default", "Font size: 16"],
    ["sv", "Standard", "Teckenstorlek: Standard", "Teckenstorlek: 16"],
  ])("in %s", (locale, fallback, nameDefault, name16) => {
    const { editor, bar } = mount([["fontSize"]], "<p>ab</p>", locale);
    const trigger = btn(bar, "fontSize");
    expect(valueText(bar)).toBe(fallback);
    expect(trigger.getAttribute("aria-label")).toBe(nameDefault);
    editor.chain().selectAll().setMark("textStyle", { fontSize: "16px" }).run();
    editor.commands.setTextSelection(2);
    expect(valueText(bar)).toBe("16");
    expect(trigger.getAttribute("aria-label")).toBe(name16);
    editor.chain().selectAll().setMark("textStyle", { fontSize: null }).run();
    editor.commands.setTextSelection(2);
    expect(valueText(bar)).toBe(fallback);
    expect(trigger.getAttribute("aria-label")).toBe(nameDefault);
  });

  it("follows the caret between sizes, and strips px from a size off the list", () => {
    const { editor, bar } = mount(
      [["fontSize"]],
      '<p><span style="font-size: 20px">ab</span>cd<span style="font-size: 13px">ef</span></p>',
    );
    editor.commands.setTextSelection(2);
    expect(valueText(bar)).toBe("20");
    editor.commands.setTextSelection(4);
    expect(valueText(bar)).toBe("Default");
    editor.commands.setTextSelection(6);
    expect(valueText(bar)).toBe("13");
  });

  it("keeps the title as the plain name and the glyph off the trigger", () => {
    const { bar } = mount([["fontSize"]], "<p>ab</p>");
    expect(btn(bar, "fontSize").title).toBe("Font size");
    expect(btn(bar, "fontSize").querySelector(".django-tiptap__glyph")).toBeNull();
  });

  it("holds every label in a hidden sizer so its width does not move", () => {
    const { bar } = mount([["fontSize"]], "<p>ab</p>", "sv", { fontSizes: ["9px", "120px"] });
    const sizer = btn(bar, "fontSize").querySelector(".django-tiptap__value-sizer");
    expect(sizer?.getAttribute("aria-hidden")).toBe("true");
    expect(Array.from(sizer?.children ?? []).map((s) => s.textContent)).toEqual([
      "Standard",
      "9",
      "120",
    ]);
  });

  it("leaves the other dropdown triggers on their glyphs", () => {
    const { bar } = mount([["fontFamily", "color", "highlight"]], "<p>ab</p>");
    for (const trigger of triggers(bar)) {
      expect(trigger.querySelector(".django-tiptap__glyph")).not.toBeNull();
      expect(trigger.querySelector(".django-tiptap__value-text")).toBeNull();
    }
    expect(btn(bar, "fontFamily").getAttribute("aria-label")).toBe("Font family");
  });
});

describe("translator interpolation", () => {
  it("fills named placeholders from params", () => {
    expect(getTranslator("en")("fontSizeValue", { name: "Font size", value: "16" })).toBe(
      "Font size: 16",
    );
    expect(getTranslator("sv")("fontSizeValue", { name: "Teckenstorlek", value: "16" })).toBe(
      "Teckenstorlek: 16",
    );
  });

  it("uses a registered locale's template and leaves unknown placeholders alone", () => {
    registerLocale("xx-aria", { fontSizeValue: "{value} ({name}) {other}" });
    expect(getTranslator("xx-aria")("fontSizeValue", { name: "N", value: "V" })).toBe("V (N) {other}");
  });

  it("returns every existing key unchanged without params", () => {
    const t = getTranslator("en");
    expect(t("fontSize")).toBe("Font size");
    expect(t("custom")).toBe("Custom…");
    expect(t("missing-key")).toBe("missing-key");
    expect(t("fontSizeValue")).toBe("{name}: {value}");
  });
});
