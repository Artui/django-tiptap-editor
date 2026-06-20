// Highlight implemented as a TextStyle attribute rendering
// `<span style="background-color: …">` — the form legacy editors emit. This
// round-trips that markup exactly, rather than converting to <mark> (which the
// corpus spike showed drops the color on parse). Registered under the config
// name "highlight".
import { Extension } from "../tiptap-runtime";

export const BackgroundColor = Extension.create({
  name: "backgroundColor",
  addOptions() {
    return { types: ["textStyle"] };
  },
  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: {
          backgroundColor: {
            default: null,
            parseHTML: (el: HTMLElement) => el.style.backgroundColor || null,
            renderHTML: (attrs: Record<string, unknown>) =>
              attrs.backgroundColor
                ? { style: `background-color: ${attrs.backgroundColor as string}` }
                : {},
          },
        },
      },
    ];
  },
});
