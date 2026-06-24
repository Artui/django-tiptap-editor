// Framework-agnostic mount / teardown. The glue watches the DOM with a single
// MutationObserver, so editors mount and tear down on ANY DOM change — no htmx /
// admin event wiring. These tests drive real DOM mutations (no synthetic events)
// and flush the observer's microtask before asserting against the live DOM.
//
// Django emits a stable id_<field>, so after a destructive swap the server
// re-renders a fresh textarea with the SAME id. The glue must re-mount on the new
// node and tear the stale editor down — not leave a bare textarea on top.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DjangoTipTap from "../src/index";

const ID = "id_content";
const FIELD = `<textarea id="${ID}" data-tiptap-config="{}">hello</textarea>`;

// MutationObserver callbacks run as microtasks; a macrotask tick drains them
// (including the no-op follow-up the observer sees from our own shell insert).
function flush(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

function plantForm(html: string): HTMLFormElement {
  const form = document.createElement("form");
  form.innerHTML = html;
  document.body.appendChild(form);
  return form;
}

function shellCount(): number {
  return document.querySelectorAll("[data-tiptap-shell]").length;
}

beforeEach(() => {
  vi.spyOn(console, "error").mockImplementation(() => {});
});

afterEach(async () => {
  // Clearing the DOM lets the observer tear down any live instance; flush so the
  // map is clean before the next test.
  document.body.innerHTML = "";
  await flush();
  vi.restoreAllMocks();
});

describe("framework-agnostic swap lifecycle", () => {
  it("mounts an editor when a textarea is inserted (no framework event)", async () => {
    const form = plantForm(FIELD);
    await flush();

    const textarea = form.querySelector("textarea") as HTMLTextAreaElement;
    expect(DjangoTipTap.get(ID)).not.toBeNull();
    expect(textarea.style.display).toBe("none");
    expect(textarea.getAttribute("data-tiptap-bound")).toBe("true");
    expect(shellCount()).toBe(1);
  });

  it("re-mounts on the swapped-in textarea and destroys the stale editor", async () => {
    const form = plantForm(FIELD);
    await flush();
    const firstTextarea = form.querySelector("textarea") as HTMLTextAreaElement;
    const firstEditor = DjangoTipTap.get(ID);

    // Server returns the form again (e.g. validation errors): an outerHTML swap
    // replaces the fragment with a brand-new textarea carrying the SAME id.
    form.innerHTML = FIELD;
    const secondTextarea = form.querySelector("textarea") as HTMLTextAreaElement;
    expect(secondTextarea).not.toBe(firstTextarea);
    await flush();

    const secondEditor = DjangoTipTap.get(ID);
    expect(secondEditor).not.toBeNull();
    expect(secondEditor).not.toBe(firstEditor);
    expect(firstEditor?.isDestroyed).toBe(true);
    expect(secondTextarea.style.display).toBe("none");
    expect(secondTextarea.getAttribute("data-tiptap-bound")).toBe("true");
    expect(shellCount()).toBe(1);
  });

  it("re-mounted editor syncs two-way (writes into the new textarea)", async () => {
    const form = plantForm(FIELD);
    await flush();
    form.innerHTML = FIELD;
    const secondTextarea = form.querySelector("textarea") as HTMLTextAreaElement;
    await flush();

    DjangoTipTap.get(ID)?.commands.insertContent(" world");
    expect(secondTextarea.value).toContain("world");
  });

  it("removes the orphaned shell when only the textarea node is swapped", async () => {
    const form = plantForm(FIELD);
    await flush();
    const firstTextarea = form.querySelector("textarea") as HTMLTextAreaElement;
    const firstShell = form.querySelector("[data-tiptap-shell]") as HTMLElement;

    // Narrow swap: replace only the <textarea>. The shell is a sibling, not a
    // child, so it is left behind as an orphan over the new textarea.
    const holder = document.createElement("div");
    holder.innerHTML = FIELD;
    const secondTextarea = holder.firstElementChild as HTMLTextAreaElement;
    firstTextarea.replaceWith(secondTextarea);
    await flush();

    expect(document.body.contains(firstShell)).toBe(false);
    expect(shellCount()).toBe(1);
    expect(secondTextarea.getAttribute("data-tiptap-bound")).toBe("true");
  });

  it("tears down the editor when its container is removed", async () => {
    const form = plantForm(FIELD);
    await flush();
    const editor = DjangoTipTap.get(ID);
    const shell = form.querySelector("[data-tiptap-shell]") as HTMLElement;

    form.remove();
    await flush();

    expect(editor?.isDestroyed).toBe(true);
    expect(DjangoTipTap.get(ID)).toBeNull();
    expect(document.body.contains(shell)).toBe(false);
  });

  it("leaves unrelated DOM removals alone", async () => {
    plantForm(FIELD);
    await flush();
    const editor = DjangoTipTap.get(ID);

    const other = document.createElement("div");
    other.textContent = "unrelated";
    document.body.appendChild(other);
    await flush();
    other.remove();
    await flush();

    expect(editor?.isDestroyed).toBe(false);
    expect(DjangoTipTap.get(ID)).toBe(editor);
  });

  it("supports additive multi-mount (admin inlines / dynamically added fields)", async () => {
    plantForm(`${FIELD}<textarea id="id_extra" data-tiptap-config="{}">more</textarea>`);
    await flush();

    expect(DjangoTipTap.get(ID)).not.toBeNull();
    expect(DjangoTipTap.get("id_extra")).not.toBeNull();
    expect(shellCount()).toBe(2);
  });

  it("ignores ProseMirror's own DOM churn (no remount on edit)", async () => {
    plantForm(FIELD);
    await flush();
    const editor = DjangoTipTap.get(ID);

    // Editing mutates the editor's contenteditable DOM (inside the shell). The
    // observer must skip it — no teardown, no second mount.
    editor?.commands.insertContent(" more text");
    await flush();

    expect(DjangoTipTap.get(ID)).toBe(editor);
    expect(editor?.isDestroyed).toBe(false);
    expect(shellCount()).toBe(1);
  });
});
