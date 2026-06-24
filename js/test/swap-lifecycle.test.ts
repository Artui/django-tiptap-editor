// Destructive-swap lifecycle. Django emits a stable id_<field> on the textarea,
// so after an outerHTML swap the server re-renders a fresh textarea with the SAME
// id. The glue must re-mount on the new node and tear the stale editor down — not
// return the dead one and leave a bare textarea on top. These tests drive the
// real document-level listeners installed by the module's bootstrap and assert
// against the live DOM.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DjangoTipTap from "../src/index";

const ID = "id_content";
const FIELD = `<textarea id="${ID}" data-tiptap-config="{}">hello</textarea>`;

function fire(name: string): void {
  document.dispatchEvent(new Event(name));
}

function plantForm(html: string): HTMLFormElement {
  const form = document.createElement("form");
  form.innerHTML = html;
  document.body.appendChild(form);
  return form;
}

function shellCount(): number {
  return document.querySelectorAll(".django-tiptap").length;
}

beforeEach(() => {
  vi.spyOn(console, "error").mockImplementation(() => {});
});

afterEach(() => {
  DjangoTipTap.destroy(ID);
  vi.restoreAllMocks();
  document.body.innerHTML = "";
});

describe("destructive swap lifecycle", () => {
  it("re-mounts on the swapped-in textarea and destroys the stale editor", () => {
    const form = plantForm(FIELD);
    fire("htmx:afterSwap"); // initial mount via the htmx re-scan path

    const firstTextarea = form.querySelector("textarea") as HTMLTextAreaElement;
    const firstEditor = DjangoTipTap.get(ID);
    expect(firstEditor).not.toBeNull();
    expect(firstTextarea.style.display).toBe("none");
    expect(firstTextarea.getAttribute("data-tiptap-bound")).toBe("true");
    expect(shellCount()).toBe(1);

    // Server returns the form again (e.g. validation errors): an outerHTML swap
    // replaces the whole fragment with a brand-new textarea carrying the SAME
    // Django id and no shell. Replacing innerHTML wipes the old textarea + shell.
    form.innerHTML = FIELD;
    const secondTextarea = form.querySelector("textarea") as HTMLTextAreaElement;
    expect(secondTextarea).not.toBe(firstTextarea);
    expect(secondTextarea.hasAttribute("data-tiptap-bound")).toBe(false);

    fire("htmx:afterSwap");

    const secondEditor = DjangoTipTap.get(ID);
    // Exactly one editor, bound to the NEW textarea, with a single shell.
    expect(secondEditor).not.toBeNull();
    expect(secondEditor).not.toBe(firstEditor);
    expect(firstEditor?.isDestroyed).toBe(true);
    expect(secondTextarea.style.display).toBe("none");
    expect(secondTextarea.getAttribute("data-tiptap-bound")).toBe("true");
    expect(shellCount()).toBe(1);
  });

  it("re-mounted editor syncs two-way (writes back into the new textarea)", () => {
    const form = plantForm(FIELD);
    fire("htmx:afterSwap");

    form.innerHTML = FIELD;
    const secondTextarea = form.querySelector("textarea") as HTMLTextAreaElement;
    fire("htmx:afterSwap");

    const editor = DjangoTipTap.get(ID);
    editor?.commands.insertContent(" world");
    // The new (not the orphaned) textarea receives the update.
    expect(secondTextarea.value).toContain("world");
  });

  it("removes the orphaned shell when only the textarea node is swapped", () => {
    const form = plantForm(FIELD);
    fire("htmx:afterSwap");

    const firstTextarea = form.querySelector("textarea") as HTMLTextAreaElement;
    const firstShell = form.querySelector(".django-tiptap") as HTMLElement;
    expect(firstShell).not.toBeNull();

    // Narrow swap: replace only the <textarea> node. The shell is a sibling, not
    // a child, so htmx leaves it behind — an orphan over the new textarea.
    const holder = document.createElement("div");
    holder.innerHTML = FIELD;
    const secondTextarea = holder.firstElementChild as HTMLTextAreaElement;
    firstTextarea.replaceWith(secondTextarea);
    expect(document.body.contains(firstShell)).toBe(true); // orphan present

    fire("htmx:afterSwap");

    // init() evicted the stale instance, whose destroy() removed the orphan.
    expect(document.body.contains(firstShell)).toBe(false);
    expect(shellCount()).toBe(1);
    expect(secondTextarea.getAttribute("data-tiptap-bound")).toBe("true");
  });

  it("tears down the editor when htmx cleans up the removed element", () => {
    const form = plantForm(FIELD);
    fire("htmx:afterSwap");

    const editor = DjangoTipTap.get(ID);
    const shell = form.querySelector(".django-tiptap") as HTMLElement;
    expect(editor).not.toBeNull();

    // A swap that drops the field entirely (e.g. replaced by a success message):
    // htmx fires beforeCleanupElement on the content it removes, and init() never
    // runs to self-heal. The event bubbles to the document-level listener.
    form.dispatchEvent(new Event("htmx:beforeCleanupElement", { bubbles: true }));

    expect(editor?.isDestroyed).toBe(true);
    expect(DjangoTipTap.get(ID)).toBeNull();
    expect(document.body.contains(shell)).toBe(false);
  });

  it("ignores beforeCleanupElement for unrelated removed content", () => {
    const form = plantForm(FIELD);
    fire("htmx:afterSwap");
    const editor = DjangoTipTap.get(ID);

    // An unrelated element being cleaned up must not touch the live editor.
    const other = document.createElement("div");
    document.body.appendChild(other);
    other.dispatchEvent(new Event("htmx:beforeCleanupElement", { bubbles: true }));

    expect(editor?.isDestroyed).toBe(false);
    expect(DjangoTipTap.get(ID)).toBe(editor);
  });

  it("still supports additive multi-mount (admin inlines / formset:added)", () => {
    const form = plantForm(
      `${FIELD}<textarea id="id_extra" data-tiptap-config="{}">more</textarea>`,
    );
    fire("formset:added");

    expect(DjangoTipTap.get(ID)).not.toBeNull();
    expect(DjangoTipTap.get("id_extra")).not.toBeNull();
    expect(shellCount()).toBe(2);

    DjangoTipTap.destroy("id_extra");
  });
});
