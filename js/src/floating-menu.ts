// Selection-anchored menus (tier-2 floating regions) without a positioning
// dependency. A bubble menu shows over a non-empty selection; a floating menu
// shows at the cursor on an empty text line. Positioned with ProseMirror's
// coordsAtPos relative to the shell (which is position: relative) — repositioned
// on selection / content changes. Deliberately lean (no tippy.js / popper); for
// pixel-perfect edge handling a consumer can still build their own via Path B.
//
// Menu controls should call preventDefault on mousedown (like the toolbar) so a
// click doesn't blur the editor and dismiss the menu.
import type { Editor } from "./tiptap-runtime";

export type FloatingKind = "bubbleMenu" | "floatingMenu";

const GAP = 8;

function shouldShow(editor: Editor, kind: FloatingKind): boolean {
  if (!editor.isEditable || !editor.view.hasFocus()) {
    return false;
  }
  const { selection } = editor.state;
  if (kind === "bubbleMenu") {
    return !selection.empty;
  }
  // floatingMenu: collapsed cursor on an empty text block.
  const { $from, empty } = selection;
  return empty && $from.parent.isTextblock && $from.parent.content.size === 0;
}

// Mount `el` as a floating menu controlled by the editor's selection. Cleanup
// happens via editor.destroy() (drops the listeners) + the shell being removed
// (drops the element), so no explicit teardown is needed by the caller.
export function mountFloatingMenu(
  editor: Editor,
  shell: HTMLElement,
  kind: FloatingKind,
  el: HTMLElement,
): void {
  el.classList.add(kind === "bubbleMenu" ? "django-tiptap__bubble" : "django-tiptap__floating");
  el.style.position = "absolute";
  el.style.zIndex = "30";
  el.style.display = "none";
  shell.appendChild(el);

  const place = (): void => {
    if (!shouldShow(editor, kind)) {
      el.style.display = "none";
      return;
    }
    const { from, to } = editor.state.selection;
    let start: { top: number; bottom: number; left: number };
    let end: { left: number };
    try {
      start = editor.view.coordsAtPos(from);
      end = editor.view.coordsAtPos(to);
    } catch {
      el.style.display = "none";
      return;
    }
    el.style.display = "";
    const shellRect = shell.getBoundingClientRect();
    const box = el.getBoundingClientRect();
    const clamp = (v: number, max: number): number => Math.max(0, Math.min(v, Math.max(0, max)));
    if (kind === "bubbleMenu") {
      let top = start.top - shellRect.top - box.height - GAP;
      if (top < 0) {
        top = start.bottom - shellRect.top + GAP; // flip below if no room above
      }
      const left = (start.left + end.left) / 2 - shellRect.left - box.width / 2;
      // Keep the menu within the editor box (overflow is clipped).
      el.style.left = `${clamp(left, shellRect.width - box.width)}px`;
      el.style.top = `${clamp(top, shellRect.height - box.height)}px`;
    } else {
      el.style.left = `${clamp(start.left - shellRect.left, shellRect.width - box.width)}px`;
      el.style.top = `${clamp(start.top - shellRect.top, shellRect.height - box.height)}px`;
    }
  };

  const hide = (): void => {
    el.style.display = "none";
  };

  editor.on("selectionUpdate", place);
  editor.on("transaction", place);
  editor.on("focus", place);
  editor.on("blur", hide);
  place();
}
