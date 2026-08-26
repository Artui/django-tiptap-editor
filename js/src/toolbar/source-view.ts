// Source-view: swap the editing surface for a raw-HTML textarea. Leaving source
// view re-parses through the schema (lossy but consistent — the editor never
// stores HTML it can't model), so what you see equals what gets saved. The bound
// form <textarea> therefore only ever holds a schema-produced value in the
// field's storage format, never raw mid-edit markup: submitting with source view
// open flushes through that same re-parse first (flushSourceView, wired to the
// form in index.ts). While in source view the rest of the toolbar is disabled.
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

function toolbarOf(editor: Editor): HTMLElement | null {
  return shellOf(editor)?.querySelector<HTMLElement>(".django-tiptap__toolbar") ?? null;
}

// Close source view: re-parse the raw HTML through the schema, which fires
// onUpdate and so writes the storage value back into the bound form textarea.
// `refocus` is false for a flush — a submit must not steal the caret.
function leaveSourceView(editor: Editor, state: SourceState, refocus: boolean): void {
  const dom = editor.view.dom as HTMLElement;
  const html = state.textarea.value;
  state.textarea.remove();
  state.note.remove();
  dom.style.display = "";
  toolbarOf(editor)?.classList.remove("is-source-mode");
  states.delete(editor);
  editor.setEditable(true);
  editor.commands.setContent(html, true);
  if (refocus) {
    editor.commands.focus();
  }
}

// Apply the open source view's content, if any, and close it. Synchronous, so
// the bound textarea is up to date by the time a submit handler reads it.
export function flushSourceView(editor: Editor): void {
  const active = states.get(editor);
  if (active) {
    leaveSourceView(editor, active, false);
  }
}

export function toggleSourceView(editor: Editor): void {
  const dom = editor.view.dom as HTMLElement;
  const content = dom.parentElement;
  if (!content) {
    return;
  }

  const active = states.get(editor);
  if (active) {
    leaveSourceView(editor, active, true);
    return;
  }

  const note = document.createElement("div");
  note.className = "django-tiptap__source-note";
  note.textContent = translatorFor(editor)("sourceNote");

  const textarea = document.createElement("textarea");
  textarea.className = "django-tiptap__source";
  textarea.spellcheck = false;
  textarea.value = editor.getHTML();

  dom.style.display = "none";
  content.appendChild(note);
  content.appendChild(textarea);
  toolbarOf(editor)?.classList.add("is-source-mode");
  // Record state before setEditable, which fires the transaction that refreshes
  // the toolbar — the source button's active state must already be observable.
  states.set(editor, { textarea, note });
  editor.setEditable(false);
  textarea.focus();
}
