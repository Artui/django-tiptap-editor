import { afterEach, describe, expect, it, vi } from "vitest";

import DjangoTipTap from "../src/index";
import type { Editor } from "../src/tiptap-runtime";

let seq = 0;

interface Field {
  textarea: HTMLTextAreaElement;
  editor: Editor;
  editable: HTMLElement;
  shell: HTMLElement;
}

function mount(markup: string): Field {
  const id = `aria-${++seq}`;
  const host = document.createElement("div");
  host.innerHTML = markup.replace(/ID/g, id);
  document.body.appendChild(host);
  const textarea = host.querySelector("textarea") as HTMLTextAreaElement;
  const editor = DjangoTipTap.init(textarea);
  const editable = editor.view.dom as HTMLElement;
  const shell = textarea.nextElementSibling as HTMLElement;
  return { textarea, editor, editable, shell };
}

const settle = (): Promise<void> => new Promise((resolve) => setTimeout(resolve, 0));

function focusins(): Element[] {
  const seen: Element[] = [];
  document.addEventListener("focusin", (event) => seen.push(event.target as Element));
  return seen;
}

afterEach(() => {
  for (const textarea of document.querySelectorAll("textarea")) {
    DjangoTipTap.destroy(textarea.id);
  }
  document.body.innerHTML = "";
});

describe("the editable carries the textarea's accessible name and state", () => {
  it("names its label and mirrors description, invalid and required", () => {
    const { textarea, editable } = mount(
      '<label for="ID" id="ID-own">Body</label>' +
        '<textarea id="ID" aria-describedby="ID-help" aria-invalid="true" required></textarea>' +
        '<div id="ID-help">Plain words only.</div>',
    );
    expect(textarea.labels?.length).toBe(1);
    expect(editable.getAttribute("aria-labelledby")).toBe(`${textarea.id}-own`);
    expect(editable.getAttribute("aria-multiline")).toBe("true");
    expect(editable.getAttribute("aria-describedby")).toBe(`${textarea.id}-help`);
    expect(editable.getAttribute("aria-invalid")).toBe("true");
    expect(editable.getAttribute("aria-required")).toBe("true");
  });

  it("gives each label without an id a deterministic one", () => {
    const { textarea, editable } = mount(
      '<label for="ID">Body</label><label for="ID" id="named">Second</label>' +
        '<label for="ID">Third</label><textarea id="ID"></textarea>',
    );
    const [first, second, third] = Array.from(textarea.labels ?? []);
    expect(first.id).toBe(`${textarea.id}-label`);
    expect(second.id).toBe("named");
    expect(third.id).toBe(`${textarea.id}-label-3`);
    expect(editable.getAttribute("aria-labelledby")).toBe(
      `${textarea.id}-label named ${textarea.id}-label-3`,
    );
  });

  it("omits state the textarea does not carry", () => {
    const { editable } = mount('<label for="ID">Body</label><textarea id="ID"></textarea>');
    for (const name of ["aria-describedby", "aria-invalid", "aria-required", "aria-label"]) {
      expect(editable.hasAttribute(name)).toBe(false);
    }
  });

  it("keeps Tiptap's textbox role and leaves contenteditable to ProseMirror", () => {
    const { editable } = mount('<label for="ID">Body</label><textarea id="ID"></textarea>');
    expect(editable.getAttribute("role")).toBe("textbox");
    expect(editable.getAttribute("contenteditable")).toBe("true");
  });
});

describe("a field with no label", () => {
  it("carries the textarea's aria-label", () => {
    const { editable } = mount('<textarea id="ID" aria-label="Message body"></textarea>');
    expect(editable.getAttribute("aria-label")).toBe("Message body");
    expect(editable.hasAttribute("aria-labelledby")).toBe(false);
  });

  it("carries the textarea's aria-labelledby", () => {
    const { textarea, editable } = mount(
      '<h3 id="ID-heading">Message</h3><textarea id="ID" aria-labelledby="ID-heading"></textarea>',
    );
    expect(editable.getAttribute("aria-labelledby")).toBe(`${textarea.id}-heading`);
  });

  it("falls back to the textarea's title", () => {
    const { editable } = mount('<textarea id="ID" title="Notes"></textarea>');
    expect(editable.getAttribute("aria-label")).toBe("Notes");
  });

  it("prefers the textarea's own aria-label over its label, as the textarea did", () => {
    const { editable } = mount(
      '<label for="ID">Body</label><textarea id="ID" aria-label="Override"></textarea>',
    );
    expect(editable.getAttribute("aria-label")).toBe("Override");
    expect(editable.hasAttribute("aria-labelledby")).toBe(false);
  });
});

describe("the editable follows the textarea after mount", () => {
  it("sets and clears aria-invalid as the textarea does", async () => {
    const { textarea, editable } = mount(
      '<label for="ID">Body</label><textarea id="ID"></textarea>',
    );
    textarea.setAttribute("aria-invalid", "true");
    await settle();
    expect(editable.getAttribute("aria-invalid")).toBe("true");
    textarea.removeAttribute("aria-invalid");
    await settle();
    expect(editable.hasAttribute("aria-invalid")).toBe(false);
  });

  it("follows required, aria-describedby and aria-label", async () => {
    const { textarea, editable } = mount('<textarea id="ID"></textarea>');
    textarea.required = true;
    textarea.setAttribute("aria-describedby", "help");
    textarea.setAttribute("aria-label", "Body");
    await settle();
    expect(editable.getAttribute("aria-required")).toBe("true");
    expect(editable.getAttribute("aria-describedby")).toBe("help");
    expect(editable.getAttribute("aria-label")).toBe("Body");
  });

  it("restores a stripped generated label id when a textarea attribute changes", async () => {
    const { textarea, editable } = mount(
      '<label for="ID">Body</label><textarea id="ID"></textarea>',
    );
    const label = textarea.labels?.[0] as HTMLLabelElement;
    label.removeAttribute("id");
    textarea.setAttribute("aria-describedby", "help");
    await settle();
    expect(label.id).toBe(`${textarea.id}-label`);
    expect(editable.getAttribute("aria-labelledby")).toBe(label.id);
  });

  it("keeps the textarea hidden and bound while it syncs", async () => {
    const { textarea } = mount('<label for="ID">Body</label><textarea id="ID"></textarea>');
    textarea.removeAttribute("style");
    textarea.setAttribute("aria-invalid", "true");
    await settle();
    expect(textarea.style.display).toBe("none");
    expect(textarea.getAttribute("data-tiptap-bound")).toBe("true");
  });
});

describe("a label wrapping the field", () => {
  const WRAPPED =
    '<label>Body <em>text</em><textarea id="ID">&lt;p&gt;Stored words&lt;/p&gt;</textarea></label>';

  it("names the editable by the label's own text, not the editor's", async () => {
    const { textarea, editable, shell } = mount(WRAPPED);
    expect(textarea.labels?.[0].contains(shell)).toBe(true);
    expect(editable.textContent).toContain("Stored words");
    expect(editable.getAttribute("aria-label")).toBe("Body text");
    expect(editable.hasAttribute("aria-labelledby")).toBe(false);
    textarea.setAttribute("aria-describedby", "help");
    await settle();
    expect(editable.getAttribute("aria-label")).toBe("Body text");
  });

  it("reads every label as text when one of them wraps the field", () => {
    const { editable } = mount(
      '<label for="ID">Lead</label><label>Body <textarea id="ID"></textarea></label>',
    );
    expect(editable.getAttribute("aria-label")).toBe("Lead Body");
    expect(editable.hasAttribute("aria-labelledby")).toBe(false);
  });

  it("does not refocus the editable for a click inside the shell", () => {
    const { editor, shell } = mount(WRAPPED);
    const toolbar = shell.querySelector(".django-tiptap__toolbar") as HTMLElement;
    const button = toolbar.querySelector("button:not([disabled])") as HTMLButtonElement;
    button.focus();
    const focus = vi.spyOn(editor.view, "focus");
    toolbar.click();
    (editor.view.dom.querySelector("p") as HTMLElement).click();
    expect(focus).not.toHaveBeenCalled();
    expect(document.activeElement).toBe(button);
  });

  it("focuses the editable for a click on the label's own text", () => {
    const { textarea, editable } = mount(WRAPPED);
    (textarea.labels?.[0].querySelector("em") as HTMLElement).click();
    expect(document.activeElement).toBe(editable);
  });
});

describe("a label click", () => {
  it("focuses the editable without resetting its selection", () => {
    const { textarea, editor, editable } = mount(
      '<label for="ID">Body</label><textarea id="ID">&lt;p&gt;Hello world&lt;/p&gt;</textarea>',
    );
    editor.commands.setTextSelection({ from: 3, to: 6 });
    const seen = focusins();
    textarea.labels?.[0].click();
    expect(document.activeElement).toBe(editable);
    expect(seen).toEqual([editable]);
    expect(editor.state.selection.from).toBe(3);
    expect(editor.state.selection.to).toBe(6);
  });

  it("focuses its own editor when two share a page", () => {
    const one = mount('<label for="ID">First</label><textarea id="ID"></textarea>');
    const two = mount('<label for="ID">Second</label><textarea id="ID"></textarea>');
    expect(one.editable.getAttribute("aria-labelledby")).toBe(`${one.textarea.id}-label`);
    expect(two.editable.getAttribute("aria-labelledby")).toBe(`${two.textarea.id}-label`);
    two.textarea.labels?.[0].click();
    expect(document.activeElement).toBe(two.editable);
    one.textarea.labels?.[0].click();
    expect(document.activeElement).toBe(one.editable);
  });

  it("is no longer handled once the editor is destroyed", () => {
    const { textarea } = mount('<label for="ID">Body</label><textarea id="ID"></textarea>');
    const label = textarea.labels?.[0] as HTMLLabelElement;
    const added = vi.spyOn(label, "addEventListener");
    const removed = vi.spyOn(label, "removeEventListener");
    DjangoTipTap.destroy(textarea.id);
    const editor = DjangoTipTap.init(textarea);
    const handler = added.mock.calls.find(([type]) => type === "click")?.[1];
    expect(handler).toBeTypeOf("function");
    DjangoTipTap.destroy(textarea.id);
    expect(removed).toHaveBeenCalledWith("click", handler);
    expect(editor.isDestroyed).toBe(true);
  });
});
