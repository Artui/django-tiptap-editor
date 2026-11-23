import { afterEach, describe, expect, it, vi } from "vitest";

import DjangoTipTap from "../src/index";
import type { TipTapConfig } from "../src/default-config";
import type { Editor } from "../src/tiptap-runtime";

let seq = 0;

interface Field {
  textarea: HTMLTextAreaElement;
  editor: Editor;
  editable: HTMLElement;
  shell: HTMLElement;
}

function mount(attrs: string, body = "<p>hello world</p>", config: TipTapConfig = {}): Field {
  const id = `editable-${++seq}`;
  const host = document.createElement("div");
  host.innerHTML =
    `<label for="${id}">Body</label><div id="${id}-help">Help</div>` +
    `<textarea id="${id}" aria-describedby="${id}-help" ${attrs}></textarea>`;
  document.body.appendChild(host);
  const textarea = host.querySelector("textarea") as HTMLTextAreaElement;
  textarea.value = body;
  const editor = DjangoTipTap.init(textarea, config);
  const editable = editor.view.dom as HTMLElement;
  const shell = textarea.nextElementSibling as HTMLElement;
  return { textarea, editor, editable, shell };
}

const settle = (): Promise<void> => new Promise((resolve) => setTimeout(resolve, 0));

function buttons(shell: HTMLElement): HTMLButtonElement[] {
  return Array.from(shell.querySelectorAll<HTMLButtonElement>(".django-tiptap__toolbar button"));
}

function button(shell: HTMLElement, key: string): HTMLButtonElement {
  const el = shell.querySelector(`[data-key="${key}"]`) as HTMLElement;
  return (el.matches("button") ? el : el.querySelector("button")) as HTMLButtonElement;
}

function pressModB(editor: Editor): void {
  editor.view.dom.dispatchEvent(
    new KeyboardEvent("keydown", { key: "b", ctrlKey: true, bubbles: true, cancelable: true }),
  );
}

function expectLocked(field: Field): void {
  expect(field.editor.isEditable).toBe(false);
  expect(field.editable.getAttribute("contenteditable")).toBe("false");
  const all = buttons(field.shell);
  expect(all.length).toBeGreaterThan(20);
  const live = all.filter((b) => !b.disabled);
  expect(live.map((b) => b.closest("[data-key]")?.getAttribute("data-key"))).toEqual([]);
}

function expectUnlocked(field: Field): void {
  expect(field.editor.isEditable).toBe(true);
  expect(field.editable.getAttribute("contenteditable")).toBe("true");
  expect(field.editable.hasAttribute("aria-disabled")).toBe(false);
  expect(field.editable.hasAttribute("aria-readonly")).toBe(false);
  expect(field.editable.getAttribute("tabindex")).toBe("0");
  for (const key of ["bold", "h1", "sourceView", "fontSize", "color"]) {
    expect(button(field.shell, key).disabled).toBe(false);
  }
  expect(button(field.shell, "undo").disabled).toBe(true);
  expect(button(field.shell, "unlink").disabled).toBe(true);
}

afterEach(() => {
  for (const textarea of document.querySelectorAll("textarea")) {
    DjangoTipTap.destroy(textarea.id);
  }
  document.body.innerHTML = "";
});

describe("a disabled or readonly textarea mounts a non-editable editor", () => {
  it("disabled: not editable, aria-disabled, every toolbar button disabled", () => {
    const field = mount("disabled");
    expectLocked(field);
    expect(field.editable.getAttribute("aria-disabled")).toBe("true");
    expect(field.editable.hasAttribute("aria-readonly")).toBe(false);
    expect(field.editable.hasAttribute("tabindex")).toBe(false);
  });

  it("readonly: not editable, aria-readonly, focusable, every toolbar button disabled", () => {
    const field = mount("readonly");
    expectLocked(field);
    expect(field.editable.getAttribute("aria-readonly")).toBe("true");
    expect(field.editable.hasAttribute("aria-disabled")).toBe(false);
    expect(field.editable.getAttribute("tabindex")).toBe("0");
  });

  it("both: disabled wins, so only aria-disabled", () => {
    const field = mount("disabled readonly");
    expectLocked(field);
    expect(field.editable.getAttribute("aria-disabled")).toBe("true");
    expect(field.editable.hasAttribute("aria-readonly")).toBe(false);
    expect(field.editable.hasAttribute("tabindex")).toBe(false);
  });

  it("an editable field keeps its toolbar's own disabled state", () => {
    expectUnlocked(mount(""));
  });
});

describe("a later disabled or readonly change is followed both ways", () => {
  it.each(["disabled", "readonly"])("%s on, then off", async (attr) => {
    const field = mount("");
    field.textarea.setAttribute(attr, "");
    await settle();
    expectLocked(field);
    expect(field.editable.getAttribute(`aria-${attr}`)).toBe("true");
    field.textarea.removeAttribute(attr);
    await settle();
    expectUnlocked(field);
  });

  it("keeps the field's name, description and multiline across setEditable", async () => {
    const field = mount("");
    field.textarea.disabled = true;
    await settle();
    expect(field.editable.getAttribute("aria-labelledby")).toBe(`${field.textarea.id}-label`);
    expect(field.editable.getAttribute("aria-describedby")).toBe(`${field.textarea.id}-help`);
    expect(field.editable.getAttribute("aria-multiline")).toBe("true");
    expect(field.editable.getAttribute("role")).toBe("textbox");
    field.textarea.disabled = false;
    await settle();
    expect(field.editable.getAttribute("aria-labelledby")).toBe(`${field.textarea.id}-label`);
    expect(field.editable.getAttribute("aria-multiline")).toBe("true");
  });

  it("closes an open source view before locking, so its close cannot unlock", async () => {
    const field = mount("");
    button(field.shell, "sourceView").click();
    const source = field.shell.querySelector(".django-tiptap__source") as HTMLTextAreaElement;
    source.value = "<p>from source</p>";
    source.dispatchEvent(new Event("input"));
    field.textarea.readOnly = true;
    await settle();
    expect(field.shell.querySelector(".django-tiptap__source")).toBeNull();
    expect(field.editor.getHTML()).toBe("<p>from source</p>");
    expectLocked(field);
  });

  it("leaves source view's own non-editable state alone on an unrelated change", async () => {
    const field = mount("");
    button(field.shell, "sourceView").click();
    field.textarea.setAttribute("aria-invalid", "true");
    await settle();
    expect(field.editor.isEditable).toBe(false);
    expect(button(field.shell, "sourceView").disabled).toBe(false);
  });

  it("closes an open toolbar panel when the field locks", async () => {
    const field = mount("");
    const trigger = button(field.shell, "color");
    trigger.click();
    expect(trigger.getAttribute("aria-expanded")).toBe("true");
    field.textarea.disabled = true;
    await settle();
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
    expect(document.querySelector("[data-tiptap-panel]")).toBeNull();
    expect(trigger.disabled).toBe(true);
  });

  it("re-enables only what the lock disabled in a custom control", async () => {
    DjangoTipTap.ui.registerButton("lockProbe", {
      title: "Probe",
      render: () => {
        const el = document.createElement("span");
        el.innerHTML = '<button type="button">on</button><button type="button" disabled>off</button>';
        return { el };
      },
    });
    const field = mount("", "<p>x</p>", { toolbar: [["bold", "lockProbe"]] });
    const probe = field.shell.querySelector('[data-key="lockProbe"]') as HTMLElement;
    const [on, off] = Array.from(probe.querySelectorAll("button"));
    field.textarea.disabled = true;
    await settle();
    expect([on.disabled, off.disabled]).toEqual([true, true]);
    expect(probe.hasAttribute("disabled")).toBe(false);
    field.textarea.disabled = false;
    await settle();
    expect([on.disabled, off.disabled]).toEqual([false, true]);
  });
});

describe("a non-editable doc does not change", () => {
  it.each(["disabled", "readonly"])("%s: neither a toolbar command nor Mod-b", (attr) => {
    const open = mount("");
    open.editor.commands.setTextSelection({ from: 1, to: 6 });
    pressModB(open.editor);
    expect(open.editor.getHTML()).toBe("<p><strong>hello</strong> world</p>");
    button(open.shell, "italic").click();
    expect(open.editor.getHTML()).toBe("<p><strong><em>hello</em></strong> world</p>");

    const shut = mount(attr);
    shut.editor.commands.setTextSelection({ from: 1, to: 6 });
    pressModB(shut.editor);
    button(shut.shell, "italic").click();
    button(shut.shell, "h1").click();
    expect(shut.editor.getHTML()).toBe("<p>hello world</p>");
  });
});

describe("mounting a locked field leaves its value alone", () => {
  it.each(["disabled", "readonly"])("%s: no input, no onChange, the value unrewritten", async (attr) => {
    const onChange = vi.fn();
    const input = vi.fn();
    document.addEventListener("input", input);
    const field = mount(attr, "<p><b>bold</b></p>", { onChange } as TipTapConfig);
    await settle();
    document.removeEventListener("input", input);
    expect(field.textarea.value).toBe("<p><b>bold</b></p>");
    expect(onChange).not.toHaveBeenCalled();
    expect(input).not.toHaveBeenCalled();
  });

  it("readonly JSON storage keeps its envelope byte for byte", async () => {
    const stored = '{"doc": {"type": "doc", "content": [{"type": "paragraph"}]}, "html": "<p></p>"}';
    const field = mount('readonly data-tiptap-storage="json"', stored);
    field.textarea.readOnly = false;
    await settle();
    field.textarea.readOnly = true;
    await settle();
    expect(field.textarea.value).toBe(stored);
  });
});
