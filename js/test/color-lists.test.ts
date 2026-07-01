// Text-color / highlight swatch palettes. The built-in lists are used when the
// per-editor config omits `textColors` / `highlightColors`; when present, config
// overrides them. The resolver runs at render time (config is per-editor), so
// two editors with different configs get different swatch grids.
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

// Render the given color control, open its dropdown, and return each swatch's
// color (read from `title`, which holds the verbatim string — `style` is
// normalised to rgb() by the CSSOM).
function swatchColors(m: Loaded, key: string, editor: unknown): string[] {
  const spec = m.getButton(key);
  if (!spec?.render) {
    throw new Error(`no render for ${key}`);
  }
  const { el } = spec.render(editor as never);
  document.body.appendChild(el);
  el.querySelector<HTMLButtonElement>(".django-tiptap__dropdown-trigger")?.click();
  const swatches = Array.from(el.querySelectorAll<HTMLElement>(".django-tiptap__swatch"));
  return swatches.map((s) => s.title);
}

beforeEach(() => {
  vi.resetModules();
});

afterEach(() => {
  vi.restoreAllMocks();
  document.body.innerHTML = "";
});

describe("text-color / highlight swatch palettes", () => {
  it("uses the built-in palettes when config omits the keys", async () => {
    const m = await load();
    m.registerBuiltInButtons();
    const editor = makeEditor(m);

    expect(swatchColors(m, "color", editor)).toEqual([
      "#1f2329", "#5c6370", "#e03e2d", "#e8710a", "#f1c40f",
      "#2dc26b", "#3598db", "#3538cd", "#9b59b6", "#ffffff",
    ]);
    expect(swatchColors(m, "highlight", editor)).toEqual([
      "#fff3a3", "#c8f7c5", "#bfe3ff", "#ffd6e7", "#ffe0b2",
    ]);

    editor.destroy();
  });

  it("uses config.textColors / config.highlightColors when provided", async () => {
    const m = await load();
    m.registerBuiltInButtons();
    const editor = makeEditor(m);
    m.setEditorConfig(editor, {
      textColors: ["#000000", "#ff0000", "rgb(0, 128, 0)"],
      highlightColors: ["#ffff00", "cyan"],
    });

    expect(swatchColors(m, "color", editor)).toEqual(["#000000", "#ff0000", "rgb(0, 128, 0)"]);
    expect(swatchColors(m, "highlight", editor)).toEqual(["#ffff00", "cyan"]);

    editor.destroy();
  });
});
