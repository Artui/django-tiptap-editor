// Inline image that keeps width / height / style (float, margin). The default
// Image is a block node and drops sizing + layout style — the corpus spike
// showed that pulls images out of their paragraph and loses dimensions. Use via
// `InlineImage.configure({ inline: true })`.
import { Image } from "../tiptap-runtime";

export const InlineImage = Image.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      width: {
        default: null,
        parseHTML: (el: HTMLElement) => el.getAttribute("width"),
        renderHTML: (attrs: Record<string, unknown>) =>
          attrs.width ? { width: attrs.width as string } : {},
      },
      height: {
        default: null,
        parseHTML: (el: HTMLElement) => el.getAttribute("height"),
        renderHTML: (attrs: Record<string, unknown>) =>
          attrs.height ? { height: attrs.height as string } : {},
      },
      style: {
        default: null,
        parseHTML: (el: HTMLElement) => el.getAttribute("style") || null,
        renderHTML: (attrs: Record<string, unknown>) =>
          attrs.style ? { style: attrs.style as string } : {},
      },
    };
  },
});
