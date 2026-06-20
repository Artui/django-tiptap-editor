// Per-editor config store, so any onClick(editor) / control can read the config
// (image URLs, merge tags, …) without threading it through every call. Set once
// at mount, mirroring the per-editor translator store.
import type { TipTapConfig } from "./default-config";
import type { Editor } from "./tiptap-runtime";

const perEditor = new WeakMap<Editor, TipTapConfig>();

export function setEditorConfig(editor: Editor, config: TipTapConfig): void {
  perEditor.set(editor, config);
}

export function configFor(editor: Editor): TipTapConfig {
  return perEditor.get(editor) ?? {};
}
