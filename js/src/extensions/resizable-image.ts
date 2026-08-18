// InlineImage plus drag-to-resize handles. Selected in buildExtensions when the
// config leaves `imageResize` on, so switching it off restores the plain inline
// image with no NodeView in the way at all.
import { imageResizeView } from "../extensions/image-resize-view";
import type { ImageViewProps } from "../extensions/image-resize-view";
import { InlineImage } from "../extensions/inline-image";

export const ResizableImage = InlineImage.extend({
  addNodeView() {
    return (props) => imageResizeView(props as unknown as ImageViewProps);
  },
});
