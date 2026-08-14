// Configurable Enter / Shift-Enter behaviour. The default (mode "paragraph")
// keeps StarterKit's semantics: Enter splits the block into a new paragraph,
// Shift-Enter inserts a hard break. "hardBreak" makes Enter insert a <br>
// (Shift-Enter unchanged); "swap" exchanges the two. Lists are exempt in every
// mode — see addKeyboardShortcuts. Registered at high priority so its bindings
// win over StarterKit's default-priority keymap, and each handler returns the
// command's own result, so when a break/split can't apply in context the editor
// falls back to the default behaviour.
import type { EnterKeyMode } from "../default-config";
import { Extension } from "../tiptap-runtime";

export type { EnterKeyMode };

export const EnterKey = Extension.create<{ mode: EnterKeyMode }>({
  name: "enterKey",
  priority: 1000,

  addOptions() {
    return { mode: "paragraph" };
  },

  addKeyboardShortcuts() {
    // Inside a list item the mode does not apply: Enter starts the next item and
    // Shift-Enter breaks the line within it, as in every editor authors come
    // from. Declining the key here (returning false) hands it to StarterKit's
    // own list keymap, which splits the item — and on an empty one falls through
    // again to lift out of the list. A <br> there would leave no way to add a
    // bullet, or to leave the list, from the keyboard at all.
    const inList = (): boolean => this.editor.isActive("listItem");
    const lineBreak = (): boolean => !inList() && this.editor.commands.setHardBreak();
    const newParagraph = (): boolean => !inList() && this.editor.commands.splitBlock();
    const shortcuts: Record<string, () => boolean> = {};
    if (this.options.mode === "hardBreak") {
      shortcuts.Enter = lineBreak;
    } else if (this.options.mode === "swap") {
      shortcuts.Enter = lineBreak;
      shortcuts["Shift-Enter"] = newParagraph;
    }
    // "paragraph" (default) adds no bindings — StarterKit's keymap stands.
    return shortcuts;
  },
});
