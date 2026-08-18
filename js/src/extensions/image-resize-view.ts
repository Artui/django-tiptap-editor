// Drag-to-resize handles for a selected image.
//
// Display size only: this changes the width/height the document asks for, never
// the uploaded file, which keeps its own resolution. The committed values are
// the unitless `width`/`height` attributes the corpus uses and the server
// renderer already emits, so a resize survives both storage formats.
//
// The wrapper this builds is a NodeView, i.e. editing chrome. It never reaches
// the stored value: getHTML() serializes from the document through the schema's
// renderHTML, not from this DOM.
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
  const width = Math.round(Math.min(Math.max(start.width + dx * DX_SIGN[corner], MIN_WIDTH), ceiling));
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

interface ImageNode {
  attrs: Record<string, unknown>;
  type: { name: string };
}

export interface ImageViewProps {
  node: ImageNode;
  editor: Editor;
  getPos: () => number | undefined;
}

interface ImageView {
  dom: HTMLElement;
  update: (node: ImageNode) => boolean;
  ignoreMutation: () => boolean;
  stopEvent: (event: Event) => boolean;
  destroy: () => void;
}

function applyAttrs(img: HTMLImageElement, attrs: Record<string, unknown>): void {
  for (const name of ["src", "alt", "title", "width", "height", "style"]) {
    const value = attrs[name];
    if (value === null || value === undefined || value === "") {
      img.removeAttribute(name);
    } else {
      img.setAttribute(name, String(value));
    }
  }
}

export function imageResizeView(props: ImageViewProps): ImageView {
  const { editor, getPos } = props;
  let node = props.node;

  const dom = document.createElement("span");
  dom.className = "django-tiptap__img";
  const img = document.createElement("img");
  applyAttrs(img, node.attrs);
  dom.appendChild(img);

  let stopDrag: (() => void) | null = null;

  function commit(size: Size): void {
    const pos = getPos();
    if (pos === undefined) {
      return;
    }
    const { state, dispatch } = editor.view;
    dispatch(
      state.tr.setNodeMarkup(pos, undefined, {
        ...node.attrs,
        width: String(size.width),
        height: String(size.height),
        style: withoutSizeDeclarations(node.attrs.style),
      }),
    );
  }

  function startDrag(event: MouseEvent, corner: Corner): void {
    // The handle is chrome, not content: without this the mousedown reaches
    // ProseMirror and moves the selection out from under the drag.
    event.preventDefault();
    event.stopPropagation();

    const rect = img.getBoundingClientRect();
    const start: Size = {
      width: rect.width || Number(node.attrs.width) || img.naturalWidth,
      height: rect.height || Number(node.attrs.height) || img.naturalHeight,
    };
    const startX = event.clientX;
    const max = editor.view.dom.clientWidth;
    let latest = start;

    const onMove = (moveEvent: MouseEvent): void => {
      latest = nextSize(start, moveEvent.clientX - startX, corner, max);
      // Preview through inline style so the drag stays at 60fps and produces no
      // undo steps; the single transaction lands on mouseup.
      img.style.width = `${latest.width}px`;
      img.style.height = `${latest.height}px`;
    };
    const onUp = (): void => {
      stopDrag?.();
      img.style.width = "";
      img.style.height = "";
      commit(latest);
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
    dom.appendChild(handle);
  }

  return {
    dom,
    update(updated: ImageNode): boolean {
      if (updated.type.name !== node.type.name) {
        return false;
      }
      node = updated;
      applyAttrs(img, updated.attrs);
      return true;
    },
    // This DOM is ours to maintain; re-parsing it would fight the drag preview.
    ignoreMutation: () => true,
    stopEvent: (event: Event) =>
      event.target instanceof HTMLElement &&
      event.target.classList.contains("django-tiptap__img-handle"),
    destroy: () => stopDrag?.(),
  };
}
