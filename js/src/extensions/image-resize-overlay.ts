// Drag-to-resize handles for the selected image, drawn as an overlay that
// follows the image rather than as a wrapper around it.
//
// The wrapper is what a NodeView would give us, and it is exactly what we must
// avoid: the caret's height is taken from the box beside it, so a bare <img>
// (an inline replaced element) gets a caret spanning the image, while an
// inline-block wrapper drops it to the text strut. Leaving the image untouched
// in the document keeps the caret, the line box, and the serialized value
// identical to the no-resize path; the handles float above it instead.
//
// Display size only: this changes the width/height the document asks for, never
// the uploaded file, which keeps its own resolution.
import type { Editor } from "../tiptap-runtime";

// Below this the handles have nothing left to grab.
const MIN_WIDTH = 24;

const CORNERS = ["nw", "ne", "sw", "se"] as const;
export type Corner = (typeof CORNERS)[number];

// A west handle grows the image as the pointer travels left, an east one as it
// travels right.
const DX_SIGN: Record<Corner, number> = { nw: -1, ne: 1, sw: -1, se: 1 };

export interface Size {
  width: number;
  height: number;
}

// Pure so the drag maths is testable without layout: jsdom reports every box as
// zero-sized, which no amount of synthetic mouse events can fix.
export function nextSize(start: Size, dx: number, corner: Corner, max: number): Size {
  const ratio = start.width > 0 ? start.height / start.width : 1;
  // A non-positive max means "unconstrained" — an editor that is hidden (or not
  // yet laid out) reports zero width, and clamping to that would collapse every
  // image to the minimum.
  const ceiling = max > MIN_WIDTH ? max : Number.POSITIVE_INFINITY;
  const width = Math.round(
    Math.min(Math.max(start.width + dx * DX_SIGN[corner], MIN_WIDTH), ceiling),
  );
  return { width, height: Math.round(width * ratio) };
}

// Legacy content carries its size as `style="width: 500px"`, which outranks the
// width attribute — leave it in place and a resize would appear to do nothing.
// Only the sizing declarations go; float and margin are what the corpus needs
// preserved.
export function withoutSizeDeclarations(style: unknown): string | null {
  if (typeof style !== "string") {
    return null;
  }
  const kept = style
    .split(";")
    .filter((decl) => decl.trim() && !/^\s*(width|height)\s*:/i.test(decl))
    .map((decl) => decl.trim());
  return kept.length ? `${kept.join("; ")};` : null;
}

interface SelectedImage {
  pos: number;
  attrs: Record<string, unknown>;
  dom: HTMLElement;
}

// The selection is only ever a node selection on an image here; anything else
// means the overlay hides. Read structurally so the module needs no
// prosemirror-state import of its own.
function selectedImage(editor: Editor): SelectedImage | null {
  const selection = editor.state.selection as unknown as {
    node?: { type: { name: string }; attrs: Record<string, unknown> };
    from: number;
  };
  const node = selection.node;
  if (!node || node.type.name !== "image") {
    return null;
  }
  const dom = editor.view.nodeDOM(selection.from) as HTMLElement | null;
  return dom ? { pos: selection.from, attrs: node.attrs, dom } : null;
}

export interface ImageResizeOverlay {
  sync: () => void;
  destroy: () => void;
}

export function createImageResizeOverlay(editor: Editor): ImageResizeOverlay {
  // The scroll container, so the overlay scrolls with the content it tracks
  // instead of needing a scroll listener to chase it.
  const container = editor.view.dom.parentElement;
  if (!container) {
    return { sync: () => {}, destroy: () => {} };
  }

  const root = document.createElement("div");
  root.className = "django-tiptap__img-overlay";
  root.hidden = true;
  container.appendChild(root);

  let stopDrag: (() => void) | null = null;

  function place(rect: { left: number; top: number; width: number; height: number }): void {
    const box = container!.getBoundingClientRect();
    root.style.left = `${rect.left - box.left + container!.scrollLeft}px`;
    root.style.top = `${rect.top - box.top + container!.scrollTop}px`;
    root.style.width = `${rect.width}px`;
    root.style.height = `${rect.height}px`;
  }

  function sync(): void {
    const target = selectedImage(editor);
    if (!target) {
      root.hidden = true;
      return;
    }
    root.hidden = false;
    place(target.dom.getBoundingClientRect());
  }

  function commit(target: SelectedImage, size: Size): void {
    const { state, dispatch } = editor.view;
    dispatch(
      state.tr.setNodeMarkup(target.pos, undefined, {
        ...target.attrs,
        width: String(size.width),
        height: String(size.height),
        style: withoutSizeDeclarations(target.attrs.style),
      }),
    );
    // setNodeMarkup replaces the node, and the node selection maps through that
    // step to a text position *before* the image -- so without this the caret
    // lands in front of the image the moment a drag ends, and the handles go
    // with it. Re-assert the selection so the image stays selected and can be
    // dragged again. Selection-only, so it adds no undo step of its own.
    editor.commands.setNodeSelection(target.pos);
  }

  function startDrag(event: MouseEvent, corner: Corner): void {
    const target = selectedImage(editor);
    if (!target) {
      return;
    }
    // The handle is chrome, not content: without this the mousedown reaches
    // ProseMirror and drops the node selection the drag depends on.
    event.preventDefault();
    event.stopPropagation();

    const rect = target.dom.getBoundingClientRect();
    const start: Size = {
      width: rect.width || Number(target.attrs.width) || 0,
      height: rect.height || Number(target.attrs.height) || 0,
    };
    const startX = event.clientX;
    const max = editor.view.dom.clientWidth;
    let latest = start;

    const onMove = (moveEvent: MouseEvent): void => {
      latest = nextSize(start, moveEvent.clientX - startX, corner, max);
      // Preview through inline style so the drag stays smooth and produces no
      // undo steps; the single transaction lands on mouseup.
      target.dom.style.width = `${latest.width}px`;
      target.dom.style.height = `${latest.height}px`;
      place({ left: rect.left, top: rect.top, width: latest.width, height: latest.height });
    };
    const onUp = (): void => {
      stopDrag?.();
      target.dom.style.width = "";
      target.dom.style.height = "";
      commit(target, latest);
      sync();
    };
    stopDrag = () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      stopDrag = null;
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  }

  for (const corner of CORNERS) {
    const handle = document.createElement("span");
    handle.className = `django-tiptap__img-handle django-tiptap__img-handle--${corner}`;
    handle.addEventListener("mousedown", (event) => startDrag(event, corner));
    root.appendChild(handle);
  }

  // Reflow moves the image out from under the overlay; a selection change is
  // not involved, so the editor's own update hooks never fire.
  const onWindowResize = (): void => sync();
  window.addEventListener("resize", onWindowResize);

  return {
    sync,
    destroy: () => {
      stopDrag?.();
      window.removeEventListener("resize", onWindowResize);
      root.remove();
    },
  };
}
