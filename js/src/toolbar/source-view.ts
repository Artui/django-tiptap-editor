// Source-view: swap the editing surface for a raw-HTML textarea. Leaving source
// view re-parses through the schema (lossy but consistent — the editor never
// stores HTML it can't model), so what you see equals what gets saved. While in
// source view the bound form <textarea> is kept in sync, and the rest of the
// toolbar is disabled.
import { translatorFor } from "../i18n";
import type { Editor } from "../tiptap-runtime";

interface SourceState {
  textarea: HTMLTextAreaElement;
  note: HTMLElement;
}

const states = new WeakMap<Editor, SourceState>();

export function isSourceActive(editor: Editor): boolean {
  return states.has(editor);
}

function shellOf(editor: Editor): HTMLElement | null {
  return (editor.view.dom as HTMLElement).closest(".django-tiptap");
}

function boundFormTextarea(editor: Editor): HTMLTextAreaElement | null {
  const prev = shellOf(editor)?.previousElementSibling;
  return prev instanceof HTMLTextAreaElement ? prev : null;
}

export function toggleSourceView(editor: Editor): void {
  const dom = editor.view.dom as HTMLElement;
  const content = dom.parentElement;
  const shell = shellOf(editor);
  const toolbar = shell?.querySelector<HTMLElement>(".django-tiptap__toolbar");
  if (!content) {
    return;
  }

  const active = states.get(editor);
  if (active) {
    const html = active.textarea.value;
    active.textarea.remove();
    active.note.remove();
    dom.style.display = "";
    toolbar?.classList.remove("is-source-mode");
    states.delete(editor);
    editor.setEditable(true);
    // Re-parse through the schema (fires onUpdate → form textarea sync).
    editor.commands.setContent(html, true);
    editor.commands.focus();
    return;
  }

  const note = document.createElement("div");
  note.className = "django-tiptap__source-note";
  note.textContent = translatorFor(editor)("sourceNote");

  const textarea = document.createElement("textarea");
  textarea.className = "django-tiptap__source";
  textarea.spellcheck = false;
  textarea.value = editor.getHTML();

  const form = boundFormTextarea(editor);
  if (form) {
    textarea.addEventListener("input", () => {
      form.value = textarea.value;
    });
  }

  dom.style.display = "none";
  content.appendChild(note);
  content.appendChild(textarea);
  toolbar?.classList.add("is-source-mode");
  // Record state before setEditable, which fires the transaction that refreshes
  // the toolbar — the source button's active state must already be observable.
  states.set(editor, { textarea, note });
  editor.setEditable(false);
  textarea.focus();
}
