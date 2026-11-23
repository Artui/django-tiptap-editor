import type { Editor } from "../tiptap-runtime";

// Kept apart from isEditable, which source view also turns off while its own button stays live.
const locked = new WeakSet<Editor>();

export function setLocked(editor: Editor, on: boolean): void {
  if (on) {
    locked.add(editor);
  } else {
    locked.delete(editor);
  }
}

export function isLocked(editor: Editor): boolean {
  return locked.has(editor);
}
