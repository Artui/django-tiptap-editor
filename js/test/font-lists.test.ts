// Font-family / font-size dropdown presets. The built-in lists are used when the
// per-editor config omits `fontFamilies` / `fontSizes`; when present, config
// overrides them. The resolver runs at render time (config is per-editor), so
// two editors with different configs get different dropdown contents.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

async function load() {
  const runtime = await import("../src/tiptap-runtime");
  const { buildExtensions } = await import("../src/build-extensions");
  const { setEditorConfig } = await import("../src/editor-config");
  const { getButton } = await import("../src/toolbar/button-registry");
  const { registerBuiltInButtons } = await import("../src/toolbar/built-in-buttons");
  return { runtime, buildExtensions, setEditorConfig, getButton, registerBuiltInButtons };
}

type Loaded = Awaited<ReturnType<typeof load>>;

function makeEditor(m: Loaded) {
  const content = document.createElement("div");
  content.className = "django-tiptap__content";
  document.body.appendChild(content);
  return new m.runtime.Editor({
    element: content,
    content: "<p>hello world</p>",
    extensions: m.buildExtensions({}, { tiptap: {}, locale: "en", t: (k: string) => k }),
  });
}

// Render the given built-in control, open its dropdown, and return the labels of
// the preset items (excluding the leading "Default" entry).
function presetLabels(m: Loaded, key: string, editor: unknown): string[] {
  const spec = m.getButton(key);
  if (!spec?.render) {
    throw new Error(`no render for ${key}`);
  }
  const { el } = spec.render(editor as never);
  document.body.appendChild(el);
  const trigger = el.querySelector<HTMLButtonElement>(".django-tiptap__dropdown-trigger");
  trigger?.click();
  const items = Array.from(el.querySelectorAll(".django-tiptap__menu-item"));
  return items.map((i) => i.textContent ?? "").slice(1);
}

// The trigger label for a preset item's inline font-family style (family only).
function presetStyles(m: Loaded, key: string, editor: unknown): string[] {
  const spec = m.getButton(key);
  const { el } = spec!.render!(editor as never);
  document.body.appendChild(el);
  el.querySelector<HTMLButtonElement>(".django-tiptap__dropdown-trigger")?.click();
  const items = Array.from(el.querySelectorAll<HTMLElement>(".django-tiptap__menu-item"));
  return items.map((i) => i.style.fontFamily).slice(1);
}

beforeEach(() => {
  vi.resetModules();
});

afterEach(() => {
  vi.restoreAllMocks();
  document.body.innerHTML = "";
});

describe("font-family / font-size dropdown presets", () => {
  it("uses the built-in lists when config omits the keys", async () => {
    const m = await load();
    m.registerBuiltInButtons();
    const editor = makeEditor(m);

    expect(presetLabels(m, "fontSize", editor)).toEqual([
      "12", "14", "16", "18", "24", "30", "36",
    ]);
    expect(presetLabels(m, "fontFamily", editor)).toEqual([
      "Arial", "Georgia", "Times New Roman", "Courier New", "Verdana", "system-ui",
    ]);

    editor.destroy();
  });

  it("uses config.fontSizes / config.fontFamilies when provided", async () => {
    const m = await load();
    m.registerBuiltInButtons();
    const editor = makeEditor(m);
    m.setEditorConfig(editor, {
      fontSizes: ["12px", "14px", "16px", "20px", "28px"],
      fontFamilies: ["Tahoma, sans-serif", "Roboto, sans-serif"],
    });

    expect(presetLabels(m, "fontSize", editor)).toEqual(["12", "14", "16", "20", "28"]);
    expect(presetLabels(m, "fontFamily", editor)).toEqual(["Tahoma", "Roboto"]);
    // styleOption still styles each family item with its own stack.
    expect(presetStyles(m, "fontFamily", editor)).toEqual([
      "Tahoma, sans-serif",
      "Roboto, sans-serif",
    ]);

    editor.destroy();
  });
});
