// Tier-2 / tier-3 theming: region + shell renderers. Asserts the assembled DOM
// reflects a custom toolbar region, a custom statusbar region, and a full shell
// override, plus the registry's guard rails (deferred + unknown regions).
//
// The renderer + button registries are module-global, so each test runs against
// a freshly imported module graph (vi.resetModules) to stay isolated.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

async function load() {
  const runtime = await import("../src/tiptap-runtime");
  const { buildExtensions } = await import("../src/build-extensions");
  const { buildShell } = await import("../src/build-shell");
  const renderers = await import("../src/renderers");
  const { registerBuiltInButtons } = await import("../src/toolbar/built-in-buttons");
  const { getTranslator } = await import("../src/i18n");
  return { runtime, buildExtensions, buildShell, renderers, registerBuiltInButtons, getTranslator };
}

type Loaded = Awaited<ReturnType<typeof load>>;

function makeEditor(m: Loaded, content: HTMLElement) {
  document.body.appendChild(content);
  return new m.runtime.Editor({
    element: content,
    content: "<p>hello world</p>",
    extensions: m.buildExtensions({}, { tiptap: {}, locale: "en", t: (k: string) => k }),
  });
}

function contentHost(): HTMLElement {
  const content = document.createElement("div");
  content.className = "django-tiptap__content";
  return content;
}

beforeEach(() => {
  vi.resetModules();
});

afterEach(() => {
  vi.restoreAllMocks();
  document.body.innerHTML = "";
});

describe("region + shell renderers", () => {
  it("builds the default shell: toolbar, content, and no statusbar", async () => {
    const m = await load();
    m.registerBuiltInButtons();
    const content = contentHost();
    const editor = makeEditor(m, content);

    const shell = m.buildShell(editor, {}, content, m.getTranslator("en"));
    document.body.appendChild(shell.el);

    expect(shell.el.classList.contains("django-tiptap")).toBe(true);
    expect(shell.el.querySelector(".django-tiptap__toolbar")).not.toBeNull();
    expect(shell.el.querySelector(".django-tiptap__content")).toBe(content);
    expect(shell.el.querySelector(".django-tiptap__statusbar")).toBeNull();
    // refresh is wired to the built-in toolbar and is safe to call.
    expect(() => shell.refresh()).not.toThrow();

    editor.destroy();
  });

  it("setRenderer('toolbar') replaces the default toolbar with the custom node", async () => {
    const m = await load();
    m.registerBuiltInButtons();
    let received: { editor: unknown; config: unknown; t: (k: string) => string; getButton: (k: string) => unknown } | undefined;
    m.renderers.setRenderer("toolbar", (ctx) => {
      received = ctx;
      const el = document.createElement("div");
      el.className = "my-toolbar";
      el.textContent = "custom toolbar";
      return el;
    });

    const content = contentHost();
    const editor = makeEditor(m, content);
    const shell = m.buildShell(editor, { foo: 1 }, content, m.getTranslator("en"));

    expect(shell.el.querySelector(".my-toolbar")).not.toBeNull();
    expect(shell.el.querySelector(".django-tiptap__toolbar")).toBeNull();
    // The content region is untouched by a toolbar override.
    expect(shell.el.querySelector(".django-tiptap__content")).toBe(content);
    // ctx surface: editor, config, translator, and a built-in button resolver.
    expect(received?.editor).toBe(editor);
    expect(received?.config).toEqual({ foo: 1 });
    expect(received?.t("bold")).toBe("Bold");
    expect(received?.getButton("bold")).toBeTruthy();

    editor.destroy();
  });

  it("setRenderer('statusbar') appends a bottom region while keeping the toolbar", async () => {
    const m = await load();
    m.registerBuiltInButtons();
    m.renderers.setRenderer("statusbar", (ctx) => {
      const el = document.createElement("div");
      el.className = "django-tiptap__statusbar";
      el.textContent = ctx.t("close");
      return el;
    });

    const content = contentHost();
    const editor = makeEditor(m, content);
    const shell = m.buildShell(editor, {}, content, m.getTranslator("en"));
    document.body.appendChild(shell.el);

    const status = shell.el.querySelector(".django-tiptap__statusbar");
    expect(status).not.toBeNull();
    expect(status?.textContent).toBe("Close");
    // Statusbar comes after the content in DOM order.
    const order = content.compareDocumentPosition(status as Node);
    expect(order & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    // Only the statusbar was overridden — the default toolbar is still present.
    expect(shell.el.querySelector(".django-tiptap__toolbar")).not.toBeNull();

    editor.destroy();
  });

  it("setShellRenderer hands over the whole shell and hosts the content", async () => {
    const m = await load();
    let received: { content: HTMLElement; editor: unknown } | undefined;
    m.renderers.setShellRenderer((ctx) => {
      received = ctx;
      const root = document.createElement("section");
      root.className = "my-shell";
      const header = document.createElement("header");
      header.textContent = "custom shell";
      root.appendChild(header);
      root.appendChild(ctx.content); // consumer places the editor host
      return root;
    });

    const content = contentHost();
    const editor = makeEditor(m, content);
    const shell = m.buildShell(editor, {}, content, m.getTranslator("en"));
    document.body.appendChild(shell.el);

    expect(shell.el.classList.contains("my-shell")).toBe(true);
    expect(shell.el.classList.contains("django-tiptap")).toBe(false);
    expect(shell.el.contains(content)).toBe(true);
    // No default chrome is built when the whole shell is overridden.
    expect(shell.el.querySelector(".django-tiptap__toolbar")).toBeNull();
    expect(received?.content).toBe(content);
    expect(received?.editor).toBe(editor);
    // Shell-renderer refresh is a safe no-op (the consumer owns reactivity).
    expect(() => shell.refresh()).not.toThrow();

    editor.destroy();
  });

  it("warns and ignores deferred regions (bubbleMenu / floatingMenu)", async () => {
    const m = await load();
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const fn = () => document.createElement("div");

    m.renderers.setRenderer("bubbleMenu", fn);
    m.renderers.setRenderer("floatingMenu", fn);

    expect(warn).toHaveBeenCalledTimes(2);
    expect(m.renderers.getRenderer("bubbleMenu" as never)).toBeUndefined();
    expect(m.renderers.getRenderer("floatingMenu" as never)).toBeUndefined();
  });

  it("errors and ignores an unknown region", async () => {
    const m = await load();
    const err = vi.spyOn(console, "error").mockImplementation(() => {});

    m.renderers.setRenderer("sidebar", () => document.createElement("div"));

    expect(err).toHaveBeenCalledTimes(1);
    expect(m.renderers.getRenderer("sidebar" as never)).toBeUndefined();
  });
});
