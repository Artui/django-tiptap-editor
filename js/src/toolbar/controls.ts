// Dropdown controls for the textStyle attributes (font size / family, text
// color, highlight). All four are textStyle marks, so they apply uniformly via
// setMark — which merges, so setting one doesn't clear the others.
import { translatorFor } from "../i18n";
import type { Editor } from "../tiptap-runtime";
import type { ButtonSpec, RenderedControl } from "./button-registry";
import { createDropdown } from "./dropdown";

function applyTextStyle(editor: Editor, attr: string, value: string | null): void {
  editor.chain().focus().setMark("textStyle", { [attr]: value }).run();
}

function menuItem(label: string, active: boolean, onPick: () => void): HTMLButtonElement {
  const item = document.createElement("button");
  item.type = "button";
  item.className = "django-tiptap__menu-item";
  item.textContent = label;
  if (active) {
    item.classList.add("is-active");
  }
  item.addEventListener("mousedown", (e) => e.preventDefault());
  item.addEventListener("click", (e) => {
    e.preventDefault();
    onPick();
  });
  return item;
}

// A static option list or a resolver that produces one from the editor. Font
// size / family use a resolver so the presets can be read from the per-editor
// config (fontSizes / fontFamilies) at render time rather than baked in.
export type SelectOptions =
  | Array<{ label: string; value: string }>
  | ((editor: Editor) => Array<{ label: string; value: string }>);

// Font size / family: a list of presets plus "Default".
export function selectControl(opts: {
  title: string;
  attr: string;
  triggerHTML: string;
  options: SelectOptions;
  styleOption?: boolean;
}): ButtonSpec {
  return {
    title: opts.title,
    render(editor: Editor): RenderedControl {
      const t = translatorFor(editor);
      const options = typeof opts.options === "function" ? opts.options(editor) : opts.options;
      const dd = createDropdown({
        title: t(opts.title),
        triggerHTML: opts.triggerHTML,
        buildPanel(close) {
          const list = document.createElement("div");
          list.className = "django-tiptap__menu";
          const current = (editor.getAttributes("textStyle")[opts.attr] as string) ?? null;
          list.appendChild(
            menuItem(t("default"), !current, () => {
              applyTextStyle(editor, opts.attr, null);
              close();
            }),
          );
          for (const opt of options) {
            const item = menuItem(opt.label, current === opt.value, () => {
              applyTextStyle(editor, opts.attr, opt.value);
              close();
            });
            if (opts.styleOption) {
              item.style.fontFamily = opt.value;
            }
            list.appendChild(item);
          }
          return list;
        },
      });
      return { el: dd.el };
    },
  };
}

export type MenuItem = { label: string; run: () => void } | "separator";

// A dropdown of command actions, rebuilt on open so items can reflect editor
// state (e.g. table-edit actions only appear inside a table).
export function commandMenuControl(opts: {
  title: string;
  triggerHTML: string;
  items: (editor: Editor) => MenuItem[];
}): ButtonSpec {
  return {
    title: opts.title,
    render(editor: Editor): RenderedControl {
      const t = translatorFor(editor);
      const dd = createDropdown({
        title: t(opts.title),
        triggerHTML: opts.triggerHTML,
        buildPanel(close) {
          const menu = document.createElement("div");
          menu.className = "django-tiptap__menu";
          for (const entry of opts.items(editor)) {
            if (entry === "separator") {
              const sep = document.createElement("div");
              sep.className = "django-tiptap__sep";
              menu.appendChild(sep);
              continue;
            }
            menu.appendChild(
              menuItem(t(entry.label), false, () => {
                entry.run();
                close();
              }),
            );
          }
          return menu;
        },
      });
      return { el: dd.el };
    },
  };
}

// A static swatch list or a resolver that produces one from the editor. Text
// color / highlight use a resolver so the swatches can be read from the
// per-editor config (textColors / highlightColors) at render time.
export type SwatchOptions = string[] | ((editor: Editor) => string[]);

// Text color / highlight: a swatch grid plus "Remove".
export function colorControl(opts: {
  title: string;
  attr: string;
  triggerHTML: string;
  swatches: SwatchOptions;
}): ButtonSpec {
  return {
    title: opts.title,
    render(editor: Editor): RenderedControl {
      const t = translatorFor(editor);
      const swatches = typeof opts.swatches === "function" ? opts.swatches(editor) : opts.swatches;
      const dd = createDropdown({
        title: t(opts.title),
        triggerHTML: opts.triggerHTML,
        buildPanel(close) {
          const panel = document.createElement("div");
          const grid = document.createElement("div");
          grid.className = "django-tiptap__swatches";
          const current = ((editor.getAttributes("textStyle")[opts.attr] as string) ?? "").toLowerCase();
          for (const color of swatches) {
            const sw = document.createElement("button");
            sw.type = "button";
            sw.className = "django-tiptap__swatch";
            sw.style.backgroundColor = color;
            sw.title = color;
            sw.setAttribute("aria-label", color);
            if (current === color.toLowerCase()) {
              sw.classList.add("is-active");
            }
            sw.addEventListener("mousedown", (e) => e.preventDefault());
            sw.addEventListener("click", (e) => {
              e.preventDefault();
              applyTextStyle(editor, opts.attr, color);
              close();
            });
            grid.appendChild(sw);
          }
          panel.appendChild(grid);
          panel.appendChild(
            menuItem(t("remove"), false, () => {
              applyTextStyle(editor, opts.attr, null);
              close();
            }),
          );
          return panel;
        },
      });
      return { el: dd.el };
    },
  };
}
