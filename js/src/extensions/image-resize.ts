// Adds the drag-to-resize overlay to the editor. Included by buildExtensions
// unless the config sets `imageResize: false`, in which case nothing here runs
// and the image node is left exactly as it is without this extension.
//
// An extension rather than a NodeView on purpose: the image node keeps its own
// plain DOM, so the caret, the line box and the serialized value are identical
// with resizing on or off. See image-resize-overlay for why that matters.
import { createImageResizeOverlay } from "../extensions/image-resize-overlay";
import type { ImageResizeOverlay } from "../extensions/image-resize-overlay";
import { Extension } from "../tiptap-runtime";

export const ImageResize = Extension.create({
  name: "imageResize",

  addStorage() {
    return { overlay: null as ImageResizeOverlay | null };
  },

  onCreate() {
    this.storage.overlay = createImageResizeOverlay(this.editor);
  },

  onSelectionUpdate() {
    this.storage.overlay?.sync();
  },

  // A doc change can resize or reflow the image the overlay is tracking (a
  // resize commit being the obvious one), without the selection moving.
  onUpdate() {
    this.storage.overlay?.sync();
  },

  onDestroy() {
    this.storage.overlay?.destroy();
    this.storage.overlay = null;
  },
});
