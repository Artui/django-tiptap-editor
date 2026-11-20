import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DjangoTipTap from "../src/index";
import type { TipTapConfig } from "../src/default-config";
import { toggleSourceView } from "../src/toolbar/source-view";
import type { Editor } from "../src/tiptap-runtime";

const DOC = {
  type: "doc",
  content: [{ type: "paragraph", content: [{ type: "text", text: "hello" }] }],
};

// What TipTapJSONField renders: json.dumps, so spaced separators and no default attrs.
const JSON_DUMPS = JSON.stringify({ doc: DOC, html: "<p>hello</p>" })
  .replace(/":/g, '": ')
  .replace(/,"/g, ', "');

type Mode = "html" | "json";

interface Mounted {
  form: HTMLFormElement;
  textarea: HTMLTextAreaElement;
  editor: Editor;
  shell: HTMLElement;
  events: string[];
  outside: HTMLInputElement;
}

let seq = 0;

function mount(mode: Mode, config: TipTapConfig = {}, value?: string): Mounted {
  const form = document.createElement("form");
  const textarea = document.createElement("textarea");
  textarea.id = `ev-${++seq}`;
  textarea.name = "body";
  if (mode === "json") {
    textarea.setAttribute("data-tiptap-storage", "json");
  }
  textarea.value = value ?? (mode === "json" ? JSON_DUMPS : "<p>hello</p>");
  const outside = document.createElement("input");
  outside.name = "title";
  form.append(textarea, outside);
  document.body.appendChild(form);
  const events: string[] = [];
  textarea.addEventListener("input", () => events.push("input"));
  textarea.addEventListener("change", () => events.push("change"));
  const editor = DjangoTipTap.init(textarea, config);
  const shell = textarea.nextElementSibling as HTMLElement;
  return { form, textarea, editor, shell, events, outside };
}

const tick = (): Promise<void> => new Promise((resolve) => setTimeout(resolve, 0));

function button(shell: HTMLElement, label: string): HTMLButtonElement {
  const el = shell.querySelector<HTMLButtonElement>(
    `.django-tiptap__toolbar button[aria-label="${label}"]`,
  );
  if (!el) {
    throw new Error(`no toolbar button ${label}`);
  }
  return el;
}

function sourceTextarea(): HTMLTextAreaElement {
  const el = document.querySelector<HTMLTextAreaElement>("textarea.django-tiptap__source");
  if (!el) {
    throw new Error("source view is not open");
  }
  return el;
}

function typeSource(html: string): void {
  const source = sourceTextarea();
  source.value = html;
  source.dispatchEvent(new Event("input", { bubbles: true }));
}

beforeEach(() => {
  vi.spyOn(console, "error").mockImplementation(() => {});
  vi.spyOn(console, "warn").mockImplementation(() => {});
  // focus() scrolls the selection into view in a frame; jsdom cannot measure a Range.
  vi.spyOn(window, "requestAnimationFrame").mockImplementation(() => 0);
});

afterEach(() => {
  vi.restoreAllMocks();
  document.body.innerHTML = "";
});

describe("input on the bound textarea", () => {
  it("fires once for an edit made only through the toolbar Bold button", async () => {
    const { textarea, editor, shell, events } = mount("html");
    editor.commands.setTextSelection({ from: 1, to: 6 });
    button(shell, "Bold").click();
    await tick();
    expect(textarea.value).toBe("<p><strong>hello</strong></p>");
    expect(events).toEqual(["input"]);
  });

  it("fires once for setTextAlign through its toolbar button", async () => {
    const { textarea, editor, shell, events } = mount("html");
    editor.commands.setTextSelection(2);
    button(shell, "Align center").click();
    await tick();
    expect(textarea.value).toContain("text-align: center");
    expect(events).toEqual(["input"]);
  });

  it("fires once for a merge tag inserted from the toolbar menu", async () => {
    const { textarea, editor, shell, events } = mount("html", {
      toolbar: [["mergeTags"]],
      mergeTags: [{ label: "Name", value: "{{ name }}" }],
    });
    editor.commands.setTextSelection(6);
    button(shell, "Merge tags").click();
    document.querySelector<HTMLButtonElement>(".django-tiptap__menu-item")?.click();
    await tick();
    expect(textarea.value).toContain("{{ name }}");
    expect(events).toEqual(["input"]);
  });

  it("fires once in JSON mode, with the envelope already written", async () => {
    const { textarea, editor, events } = mount("json");
    let seen = "";
    textarea.addEventListener("input", () => (seen = textarea.value));
    editor.chain().setTextSelection({ from: 1, to: 6 }).toggleBold().run();
    await tick();
    expect(events).toEqual(["input"]);
    expect(JSON.parse(seen).html).toBe("<p><strong>hello</strong></p>");
  });

  it.each(["html", "json"] as const)("fires nothing on mount in %s mode", async (mode) => {
    const { textarea, events } = mount(mode);
    await tick();
    expect(events).toEqual([]);
    expect(textarea.value).toBe(mode === "json" ? JSON_DUMPS : "<p>hello</p>");
  });

  it("fires nothing for setContent of identical content", async () => {
    const { editor, events } = mount("html");
    editor.commands.setContent("<p>hello</p>", { emitUpdate: true });
    await tick();
    expect(events).toEqual([]);
  });

  it.each(["html", "json"] as const)(
    "fires nothing when source view opens and closes with no edit in %s mode",
    async (mode) => {
      const { textarea, editor, events } = mount(mode);
      toggleSourceView(editor);
      toggleSourceView(editor);
      await tick();
      expect(events).toEqual([]);
      expect(textarea.value).toBe(mode === "json" ? JSON_DUMPS : "<p>hello</p>");
    },
  );

  it("is dispatched after the write, not from inside the editor's update", async () => {
    const { textarea, editor, events } = mount("html");
    let seen = "";
    textarea.addEventListener("input", () => (seen = textarea.value));
    editor.chain().setTextSelection({ from: 1, to: 6 }).toggleBold().run();
    expect(events).toEqual([]);
    await Promise.resolve();
    expect(events).toEqual(["input"]);
    expect(seen).toBe("<p><strong>hello</strong></p>");
  });

  it("lets a listener run an editor command without re-entering the update", async () => {
    const { textarea, editor, events } = mount("html");
    let depth = 0;
    let maxDepth = 0;
    const dispatch = editor.view.dispatch.bind(editor.view);
    editor.view.dispatch = (tr) => {
      depth += 1;
      maxDepth = Math.max(maxDepth, depth);
      try {
        dispatch(tr);
      } finally {
        depth -= 1;
      }
    };
    let ran = false;
    textarea.addEventListener("input", () => {
      if (!ran) {
        ran = true;
        editor.commands.toggleItalic();
      }
    });
    editor.chain().setTextSelection({ from: 1, to: 6 }).toggleBold().run();
    await tick();
    expect(textarea.value).toBe("<p><strong><em>hello</em></strong></p>");
    expect(events).toEqual(["input", "input"]);
    expect(maxDepth).toBe(1);
  });

  it("leaves config.onChange as it was, including on setEditable", () => {
    const onChange = vi.fn();
    const { editor } = mount("html", { onChange } as TipTapConfig);
    editor.setEditable(false);
    expect(onChange).toHaveBeenCalledWith("<p>hello</p>");
  });
});

describe("source view writes through", () => {
  it("hands onChange the new content on close, never the stale doc", () => {
    const onChange = vi.fn();
    const { editor } = mount("html", { onChange } as TipTapConfig);
    toggleSourceView(editor);
    onChange.mockClear();
    typeSource("<p>edited</p>");
    toggleSourceView(editor);
    expect(onChange.mock.calls.map(([html]) => html)).toEqual(["<p>edited</p>", "<p>edited</p>"]);
  });

  it("HTML mode: each keystroke updates the bound value and fires one input", async () => {
    const { textarea, editor, events } = mount("html");
    toggleSourceView(editor);
    typeSource("<p>edited<script>x</script></p>");
    await tick();
    expect(textarea.value).toBe("<p>edited</p>");
    expect(events).toEqual(["input"]);
    typeSource("<p>edited twice</p>");
    await tick();
    expect(textarea.value).toBe("<p>edited twice</p>");
    expect(events).toEqual(["input", "input"]);
    toggleSourceView(editor);
    await tick();
    expect(events).toEqual(["input", "input"]);
    expect(editor.getHTML()).toBe("<p>edited twice</p>");
  });

  it("JSON mode: each keystroke writes the envelope the close path stores", async () => {
    const { textarea, editor, events } = mount("json");
    toggleSourceView(editor);
    typeSource("<p>edited</p>");
    await tick();
    const written = textarea.value;
    expect(JSON.parse(written).html).toBe("<p>edited</p>");
    expect(events).toEqual(["input"]);
    toggleSourceView(editor);
    await tick();
    expect(events).toEqual(["input"]);
    expect(textarea.value).toBe(written);
  });

  it.each([
    ["a trailing rule", {}, "<p>a</p><hr>"],
    ["a typed URL with autolink", { autolink: true }, "<p>see https://example.com </p>"],
    ["a trailing table", {}, "<table><tbody><tr><td><p>a</p></td></tr></tbody></table>"],
  ])("stores what closing stores for %s", async (_name, config, html) => {
    const { textarea, editor, events } = mount("html", config as TipTapConfig);
    toggleSourceView(editor);
    typeSource(html);
    await tick();
    const written = textarea.value;
    toggleSourceView(editor);
    await tick();
    expect(textarea.value).toBe(written);
    expect(events).toEqual(["input"]);
  });

  it("a FormData built in a listener during a submit flush does not throw", async () => {
    const { form, textarea, editor } = mount("html");
    toggleSourceView(editor);
    sourceTextarea().value = "<p>pending</p>";
    const built: Array<string | null> = [];
    textarea.addEventListener("input", () => {
      built.push(new FormData(form).get("body") as string | null);
    });
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    form.dispatchEvent(new Event("formdata", { bubbles: true }));
    await tick();
    expect(built).toEqual(["<p>pending</p>"]);
  });
});

describe("change on the bound textarea", () => {
  it("fires once when focus leaves the shell after an edit", async () => {
    const { editor, shell, events, outside } = mount("html");
    button(shell, "Bold").focus();
    editor.chain().setTextSelection({ from: 1, to: 6 }).toggleBold().run();
    button(shell, "Italic").focus();
    outside.focus();
    await tick();
    expect(events).toEqual(["input", "change"]);
    button(shell, "Bold").focus();
    outside.focus();
    await tick();
    expect(events).toEqual(["input", "change"]);
  });

  it("does not fire when focus leaves without an edit", async () => {
    const { shell, events, outside } = mount("html");
    button(shell, "Bold").focus();
    outside.focus();
    await tick();
    expect(events).toEqual([]);
  });

  it("does not fire when focus moves to the colour picker inside the shell", async () => {
    const { editor, shell, events } = mount("html", { colorPicker: true } as TipTapConfig);
    button(shell, "Bold").focus();
    editor.chain().setTextSelection({ from: 1, to: 6 }).toggleBold().run();
    button(shell, "Text color").click();
    const picker = document.querySelector<HTMLInputElement>(".django-tiptap__picker-input");
    expect(picker).not.toBeNull();
    picker?.focus();
    await tick();
    expect(events).toEqual(["input"]);
  });

  it("does not fire when focus moves into source view, then fires on leaving", async () => {
    const { editor, shell, events, outside } = mount("html");
    button(shell, "Bold").focus();
    toggleSourceView(editor);
    expect(document.activeElement).toBe(sourceTextarea());
    typeSource("<p>edited</p>");
    await tick();
    expect(events).toEqual(["input"]);
    outside.focus();
    await tick();
    expect(events).toEqual(["input", "change"]);
  });

  it("fires at the next leave for an edit made while focus was elsewhere", async () => {
    const { editor, shell, events, outside } = mount("html");
    editor.chain().setTextSelection({ from: 1, to: 6 }).toggleBold().run();
    await tick();
    button(shell, "Bold").focus();
    outside.focus();
    await tick();
    expect(events).toEqual(["input", "change"]);
  });
});

describe("native events from the editor", () => {
  it("keep bubbling to the form, so a form listener filters on event.target", () => {
    const { form, textarea, shell } = mount("html");
    const targets: EventTarget[] = [];
    form.addEventListener("input", (event) => targets.push(event.target as EventTarget));
    const dom = shell.querySelector<HTMLElement>(".ProseMirror");
    dom?.dispatchEvent(new Event("input", { bubbles: true }));
    expect(targets).toEqual([dom]);
    expect(targets).not.toContain(textarea);
  });
});
