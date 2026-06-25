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

// htmx history (back/forward) snapshots the page innerHTML — capturing both the
// rendered shell and the hidden, data-tiptap-bound textarea — then restores that
// static markup on Back (firing htmx:historyRestore, NOT afterSwap). The restored
// snapshot is dead: a frozen shell with no ProseMirror view over a bound textarea.
// Idempotency must therefore live in the instances map (not the serialized
// attribute) so the restored field re-mounts and the snapshot shell is cleared.
describe("htmx history restore", () => {
  it("re-mounts a live editor and drops the serialized snapshot shell", async () => {
    const form = plantForm(FIELD);
    await flush();

    // What htmx caches: the rendered region, with the bound + hidden textarea and
    // the serialized shell sitting next to it.
    const snapshot = form.innerHTML;
    expect(snapshot).toContain("data-tiptap-bound");
    expect(snapshot).toContain("data-tiptap-shell");

    // Navigate away: the region is torn down (observer disposes the editor).
    form.innerHTML = "";
    await flush();
    expect(DjangoTipTap.get(ID)).toBeNull();

    // Back: htmx restores the static snapshot (no afterSwap — just DOM mutation).
    form.innerHTML = snapshot;
    await flush();

    // Exactly one LIVE editor; the dead snapshot shell is gone.
    const editor = DjangoTipTap.get(ID);
    expect(editor).not.toBeNull();
    expect(editor?.isDestroyed).toBe(false);
    expect(shellCount()).toBe(1);

    // Two-way sync proves it is the freshly-mounted editor, not the frozen shell.
    const textarea = form.querySelector("textarea") as HTMLTextAreaElement;
    expect(textarea.style.display).toBe("none");
    editor?.commands.insertContent(" world");
    expect(textarea.value).toContain("world");
  });
});

// A morphing swap (idiomorph / hx-swap="morph") reconciles the live textarea's
// attributes back to the server markup, stripping display:none + data-tiptap-bound
// and un-hiding the raw field next to the editor. Those are attribute mutations
// the body-level childList observer never sees, so a per-editor attribute observer
// re-asserts the hidden state.
describe("morphing swaps", () => {
  it("re-hides the textarea when a morph strips its style + bound flag", async () => {
    plantForm(FIELD);
    await flush();
    const textarea = document.getElementById(ID) as HTMLTextAreaElement;
    const editor = DjangoTipTap.get(ID);
    expect(textarea.style.display).toBe("none");

    // Simulate a morph reconciling the field back to the server's bare markup.
    textarea.removeAttribute("style");
    textarea.removeAttribute("data-tiptap-bound");
    await flush();

    // The per-editor attribute observer re-asserts the hidden state in place —
    // no teardown, no remount (the body observer ignores attribute mutations).
    expect(textarea.style.display).toBe("none");
    expect(textarea.getAttribute("data-tiptap-bound")).toBe("true");
    expect(DjangoTipTap.get(ID)).toBe(editor);
    expect(editor?.isDestroyed).toBe(false);
    expect(shellCount()).toBe(1);
  });

  it("stops re-asserting once the editor is destroyed", async () => {
    plantForm(FIELD);
    await flush();
    const textarea = document.getElementById(ID) as HTMLTextAreaElement;

    DjangoTipTap.destroy(ID);
    // After destroy the per-editor observer is disconnected, so a later morph is
    // no longer fought — the field is just a plain textarea again.
    textarea.removeAttribute("style");
    await flush();

    expect(textarea.style.display).toBe("");
  });

  it("does not observe attributes page-wide (no work on unrelated style churn)", async () => {
    plantForm(FIELD);
    await flush();
    const editor = DjangoTipTap.get(ID);

    // Attribute re-assertion is per-editor (attributeFilter on the bound field),
    // never a global attribute observer — so churning inline styles elsewhere on
    // the page must trigger no mount/teardown work.
    const other = document.createElement("div");
    document.body.appendChild(other);
    await flush();
    for (let i = 0; i < 25; i++) {
      other.style.color = i % 2 ? "red" : "blue";
    }
    await flush();

    expect(DjangoTipTap.get(ID)).toBe(editor);
    expect(editor?.isDestroyed).toBe(false);
    expect(shellCount()).toBe(1);
  });
});

// manualMount opts a field out of the AUTOMATIC triggers (initial scan + the DOM
// observer) so consumers can register renderers/extensions first; an EXPLICIT
// autoMount()/init() call still mounts it. The Python side already serializes the
// key into data-tiptap-config (KNOWN_CONFIG_KEYS); this is the JS read.
describe("manualMount opt-out", () => {
  const MANUAL_ID = "id_manual";
  const MANUAL = `<textarea id="${MANUAL_ID}" data-tiptap-config='{"manualMount":true}'>hi</textarea>`;

  it("is not auto-mounted on insertion (the observer skips it)", async () => {
    plantForm(MANUAL);
    await flush();

    expect(DjangoTipTap.get(MANUAL_ID)).toBeNull();
    expect(shellCount()).toBe(0);
  });

  it("mounts on an explicit autoMount() call", async () => {
    plantForm(MANUAL);
    await flush();

    DjangoTipTap.autoMount();
    expect(DjangoTipTap.get(MANUAL_ID)).not.toBeNull();
    expect(shellCount()).toBe(1);
  });

  it("mounts on an explicit init() call", async () => {
    plantForm(MANUAL);
    await flush();
    const textarea = document.getElementById(MANUAL_ID) as HTMLTextAreaElement;

    DjangoTipTap.init(textarea, { manualMount: true });
    expect(DjangoTipTap.get(MANUAL_ID)).not.toBeNull();
  });

  it("is not re-mounted by a later automatic scan once explicitly mounted", async () => {
    plantForm(MANUAL);
    await flush();
    DjangoTipTap.autoMount();
    const editor = DjangoTipTap.get(MANUAL_ID);

    // An unrelated insert fires the observer's automatic scan again; it must skip
    // the (already-mounted) manualMount field, not double-mount it.
    plantForm("<div>noise</div>");
    await flush();

    expect(DjangoTipTap.get(MANUAL_ID)).toBe(editor);
    expect(shellCount()).toBe(1);
  });

  it("still auto-mounts a normal field alongside a manualMount one", async () => {
    plantForm(`${FIELD}${MANUAL}`);
    await flush();

    expect(DjangoTipTap.get(ID)).not.toBeNull();
    expect(DjangoTipTap.get(MANUAL_ID)).toBeNull();
    expect(shellCount()).toBe(1);
  });
});
