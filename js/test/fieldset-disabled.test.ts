import { afterEach, describe, expect, it, vi } from "vitest";

import DjangoTipTap from "../src/index";
import type { Editor } from "../src/tiptap-runtime";

let seq = 0;

interface Field {
  fieldset: HTMLFieldSetElement;
  textarea: HTMLTextAreaElement;
  editor: Editor;
  editable: HTMLElement;
  shell: HTMLElement;
}

function mountIn(markup: (textarea: string) => string): Field {
  const id = `fieldset-${++seq}`;
  const host = document.createElement("div");
  host.innerHTML = markup(`<label for="${id}">Body</label><textarea id="${id}"></textarea>`);
  document.body.appendChild(host);
  const textarea = host.querySelector("textarea") as HTMLTextAreaElement;
  textarea.value = "<p>hello world</p>";
  const editor = DjangoTipTap.init(textarea);
  return {
    fieldset: host.querySelector("fieldset") as HTMLFieldSetElement,
    textarea,
    editor,
    editable: editor.view.dom as HTMLElement,
    shell: textarea.nextElementSibling as HTMLElement,
  };
}

const settle = (): Promise<void> => new Promise((resolve) => setTimeout(resolve, 0));

function liveButtons(shell: HTMLElement): HTMLButtonElement[] {
  const all = Array.from(shell.querySelectorAll<HTMLButtonElement>(".django-tiptap__toolbar button"));
  expect(all.length).toBeGreaterThan(20);
  return all.filter((b) => !b.disabled);
}

function expectDisabled(field: Field): void {
  expect(field.editor.isEditable).toBe(false);
  expect(field.editable.getAttribute("contenteditable")).toBe("false");
  expect(field.editable.getAttribute("aria-disabled")).toBe("true");
  expect(field.editable.hasAttribute("tabindex")).toBe(false);
  expect(liveButtons(field.shell)).toEqual([]);
}

function expectEditable(field: Field): void {
  expect(field.editor.isEditable).toBe(true);
  expect(field.editable.getAttribute("contenteditable")).toBe("true");
  expect(field.editable.hasAttribute("aria-disabled")).toBe(false);
  expect(liveButtons(field.shell).length).toBeGreaterThan(0);
}

afterEach(() => {
  for (const textarea of document.querySelectorAll("textarea")) {
    DjangoTipTap.destroy(textarea.id);
  }
  document.body.innerHTML = "";
});

describe("a textarea inside a disabled fieldset", () => {
  it("mounts a locked editor with aria-disabled and a disabled toolbar", () => {
    expectDisabled(mountIn((t) => `<fieldset disabled>${t}</fieldset>`));
  });

  it("is locked by a disabled outer fieldset too", () => {
    expectDisabled(mountIn((t) => `<fieldset disabled><fieldset>${t}</fieldset></fieldset>`));
  });

  it("stays editable in the fieldset's first legend", () => {
    expectEditable(mountIn((t) => `<fieldset disabled><legend>${t}</legend></fieldset>`));
  });

  it("is locked in a later legend, which the exemption does not cover", () => {
    expectDisabled(mountIn((t) => `<fieldset disabled><legend>A</legend><legend>${t}</legend></fieldset>`));
  });

  it("leaves the editable unfocused on a label click", () => {
    const field = mountIn((t) => `<fieldset disabled>${t}</fieldset>`);
    // jsdom's label.click() dispatches nothing inside a disabled fieldset; a browser's does.
    field.textarea.labels?.[0].dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(document.activeElement).not.toBe(field.editable);
  });
});

describe("toggling the fieldset after mount", () => {
  it("follows both ways", async () => {
    const field = mountIn((t) => `<fieldset>${t}</fieldset>`);
    expectEditable(field);
    field.fieldset.disabled = true;
    await settle();
    expectDisabled(field);
    field.fieldset.disabled = false;
    await settle();
    expectEditable(field);
  });

  it("follows an outer fieldset", async () => {
    const field = mountIn((t) => `<fieldset><fieldset>${t}</fieldset></fieldset>`);
    const outer = field.fieldset;
    outer.disabled = true;
    await settle();
    expectDisabled(field);
    outer.disabled = false;
    await settle();
    expectEditable(field);
  });

  it("stops following after destroy", async () => {
    const field = mountIn((t) => `<fieldset>${t}</fieldset>`);
    const setEditable = vi.spyOn(field.editor, "setEditable");
    DjangoTipTap.destroy(field.textarea.id);
    field.fieldset.disabled = true;
    await settle();
    expect(setEditable).not.toHaveBeenCalled();
  });
});
