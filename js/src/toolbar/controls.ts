// Dropdown controls for the textStyle attributes (font size / family, text
// color, highlight). All four are textStyle marks, so they apply uniformly via
// setMark — which merges, so setting one doesn't clear the others. The table
// line controls reuse them through a read/apply ValueSource.
import { configFor } from "../editor-config";
import { translatorFor } from "../i18n";
import type { Editor } from "../tiptap-runtime";
import type { ButtonSpec, RenderedControl } from "./button-registry";
import { createDropdown } from "./dropdown";
import { toolbarLabel } from "./label";
import { menuKeys } from "./menu-keys";

function applyTextStyle(editor: Editor, attr: string, value: string | null): void {
  editor.chain().focus().setMark("textStyle", { [attr]: value }).run();
}

// Where a control's value lives: a textStyle attribute, or a read/apply pair
// (the table line controls), which also says when the control is enabled.
export type ValueSource =
  | { attr: string }
  | {
      read: (editor: Editor) => string | null;
      apply: (editor: Editor, value: string | null) => void;
      enabled: (editor: Editor) => boolean;
    };

interface ValueHooks {
  read: (editor: Editor) => string | null;
  apply: (editor: Editor, value: string | null) => void;
  enabled?: (editor: Editor) => boolean;
}

function hooksOf(source: ValueSource): ValueHooks {
  if ("attr" in source) {
    return {
      read: (editor) => (editor.getAttributes("textStyle")[source.attr] as string) ?? null,
      apply: (editor, value) => applyTextStyle(editor, source.attr, value),
    };
  }
  return source;
}

// Disables the trigger while the source says so; undefined when it never does.
function enabler(hooks: ValueHooks, editor: Editor, trigger: HTMLButtonElement): (() => void) | undefined {
  const enabled = hooks.enabled;
  return enabled && (() => trigger.toggleAttribute("disabled", !enabled(editor)));
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

// Font size / family: a menu of radio items, the presets plus "Default" unless
// `defaultItem` is false (the table line width, which always has a value).
export function selectControl(
  opts: {
    title: string;
    triggerHTML: string;
    options: SelectOptions;
    styleOption?: boolean;
    showValue?: boolean;
    defaultItem?: boolean;
  } & ValueSource,
): ButtonSpec {
  const hooks = hooksOf(opts);
  const withDefault = opts.defaultItem !== false;
  return {
    title: opts.title,
    render(editor: Editor): RenderedControl {
      const t = translatorFor(editor);
      const options = typeof opts.options === "function" ? opts.options(editor) : opts.options;
      const label = toolbarLabel(configFor(editor), opts.title);
      const dd = createDropdown({
        editor,
        title: t(opts.title),
        triggerHTML: opts.triggerHTML,
        label,
        popup: "menu",
        buildPanel(close) {
          const list = document.createElement("div");
          list.className = "django-tiptap__menu";
          list.setAttribute("role", "menu");
          list.setAttribute("aria-label", t(opts.title));
          const current = hooks.read(editor);
          const radio = (item: HTMLButtonElement, checked: boolean): HTMLButtonElement => {
            item.setAttribute("role", "menuitemradio");
            item.setAttribute("aria-checked", String(checked));
            return item;
          };
          if (withDefault) {
            list.appendChild(
              radio(
                menuItem(t("default"), !current, () => {
                  hooks.apply(editor, null);
                  close();
                }),
                !current,
              ),
            );
          }
          for (const opt of options) {
            const item = menuItem(opt.label, current === opt.value, () => {
              hooks.apply(editor, opt.value);
              close();
            });
            if (opts.styleOption) {
              item.style.fontFamily = opt.value;
            }
            list.appendChild(radio(item, current === opt.value));
          }
          menuKeys(list);
          return list;
        },
      });
      const enable = enabler(hooks, editor, dd.trigger);
      // A label replaces the readout, so the trigger keeps one name.
      if (!opts.showValue || label) {
        return enable ? { el: dd.el, refresh: enable } : { el: dd.el };
      }
      const labels = options.map((o) => o.label);
      const readout = valueReadout(withDefault ? [t("default"), ...labels] : labels);
      dd.trigger.prepend(readout.el);
      const refresh = (): void => {
        enable?.();
        const current = hooks.read(editor);
        const text = current
          ? (options.find((o) => o.value === current)?.label ?? current.replace(/px$/, ""))
          : t("default");
        readout.text.textContent = text;
        dd.trigger.setAttribute("aria-label", t(`${opts.title}Value`, { name: t(opts.title), value: text }));
      };
      refresh();
      return { el: dd.el, refresh };
    },
  };
}

// The visible value over an invisible stack of every label in one grid cell, so the
// trigger is as wide as its widest label and never jitters as the value changes.
function valueReadout(labels: string[]): { el: HTMLElement; text: HTMLElement } {
  const el = document.createElement("span");
  el.className = "django-tiptap__value";
  const text = document.createElement("span");
  text.className = "django-tiptap__value-text";
  const sizer = document.createElement("span");
  sizer.className = "django-tiptap__value-sizer";
  sizer.setAttribute("aria-hidden", "true");
  for (const label of labels) {
    const span = document.createElement("span");
    span.textContent = label;
    sizer.appendChild(span);
  }
  el.append(text, sizer);
  return { el, text };
}

// `checked` makes the item a menuitemcheckbox showing that state (the table's lines).
export type MenuItem = { label: string; run: () => void; checked?: boolean } | "separator";

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
        editor,
        title: t(opts.title),
        triggerHTML: opts.triggerHTML,
        label: toolbarLabel(configFor(editor), opts.title),
        popup: "menu",
        buildPanel(close) {
          const menu = document.createElement("div");
          menu.className = "django-tiptap__menu";
          const entries = opts.items(editor);
          // An empty menu (mergeTags unset) is no menu: a keyboard open leaves focus on the trigger.
          if (entries.length) {
            menu.setAttribute("role", "menu");
            menu.setAttribute("aria-label", t(opts.title));
          }
          for (const entry of entries) {
            if (entry === "separator") {
              const sep = document.createElement("div");
              sep.className = "django-tiptap__sep";
              sep.setAttribute("role", "separator");
              menu.appendChild(sep);
              continue;
            }
            const item = menuItem(t(entry.label), entry.checked === true, () => {
              entry.run();
              close();
            });
            if (entry.checked === undefined) {
              item.setAttribute("role", "menuitem");
            } else {
              item.setAttribute("role", "menuitemcheckbox");
              item.setAttribute("aria-checked", String(entry.checked));
            }
            menu.appendChild(item);
          }
          menuKeys(menu);
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

// Six-digit hex is the only form <input type="color"> accepts; a swatch or
// stored value in any other notation (rgb(), a named color) can't seed it, so
// the picker opens on black rather than silently showing a wrong color.
const HEX6_RE = /^#[0-9a-f]{6}$/i;
const RGB_RE = /^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*1\s*)?\)$/i;

// A saved colour comes back as the rgb() the browser wrote, so swatches compare in lower-case hex.
function asHex(color: string): string {
  const rgb = RGB_RE.exec(color.trim());
  if (!rgb) {
    return color.trim().toLowerCase();
  }
  return `#${rgb.slice(1, 4).map((n) => Number(n).toString(16).padStart(2, "0")).join("")}`;
}

// The optional native picker row under the swatch grid, shown when the editor's
// config opts in via `colorPicker`. Committing on "change" (not "input") keeps
// one transaction per pick instead of one per drag step.
//
// The native control is styled out of the way rather than shown raw: it sits at
// opacity 0 over the whole row, beside a rainbow chip sized like a swatch, so the
// row reads as one more entry in the panel instead of an OS widget dropped into
// it. The chip is the affordance; the input on top is what the click lands on.
//
// The row is a div, not a <label>: host label rules (Django admin's
// `.aligned label`) outrank a single class and broke its layout. The input is
// named with aria-label instead, and covering the row keeps the whole row
// clickable as the label made it.
function pickerRow(
  apply: (value: string) => void,
  label: string,
  current: string,
  close: () => void,
): HTMLElement {
  const row = document.createElement("div");
  row.className = "django-tiptap__picker";
  row.title = label;
  const chip = document.createElement("span");
  chip.className = "django-tiptap__picker-chip";
  const input = document.createElement("input");
  input.type = "color";
  input.className = "django-tiptap__picker-input";
  input.setAttribute("aria-label", label);
  input.value = HEX6_RE.test(current) ? current : "#000000";
  const text = document.createElement("span");
  text.className = "django-tiptap__picker-label";
  text.textContent = label;
  row.append(chip, text, input);
  // No preventDefault on mousedown here, unlike every other control: that is
  // what would stop the native picker from opening. Losing DOM focus is safe —
  // the ProseMirror selection lives in editor state, and the apply hook's
  // chain().focus() restores it before the value is applied.
  input.addEventListener("change", () => {
    apply(input.value);
    close();
  });
  return row;
}

// Text color / highlight: a non-modal dialog of a swatch grid, an optional native
// picker and "Remove" (an <input> cannot live in a menu); Tab walks it in DOM order.
export function colorControl(
  opts: {
    title: string;
    triggerHTML: string;
    swatches: SwatchOptions;
    picker?: (editor: Editor) => boolean;
  } & ValueSource,
): ButtonSpec {
  const hooks = hooksOf(opts);
  return {
    title: opts.title,
    render(editor: Editor): RenderedControl {
      const t = translatorFor(editor);
      const swatches = typeof opts.swatches === "function" ? opts.swatches(editor) : opts.swatches;
      const dd = createDropdown({
        editor,
        title: t(opts.title),
        triggerHTML: opts.triggerHTML,
        label: toolbarLabel(configFor(editor), opts.title),
        popup: "dialog",
        buildPanel(close) {
          const panel = document.createElement("div");
          panel.setAttribute("role", "dialog");
          panel.setAttribute("aria-label", t(opts.title));
          const grid = document.createElement("div");
          grid.className = "django-tiptap__swatches";
          const current = asHex(hooks.read(editor) ?? "");
          for (const color of swatches) {
            const sw = document.createElement("button");
            sw.type = "button";
            sw.className = "django-tiptap__swatch";
            sw.style.backgroundColor = color;
            sw.title = color;
            sw.setAttribute("aria-label", color);
            const pressed = current === asHex(color);
            sw.classList.toggle("is-active", pressed);
            sw.setAttribute("aria-pressed", String(pressed));
            sw.addEventListener("mousedown", (e) => e.preventDefault());
            sw.addEventListener("click", (e) => {
              e.preventDefault();
              hooks.apply(editor, color);
              close();
            });
            grid.appendChild(sw);
          }
          panel.appendChild(grid);
          if (opts.picker?.(editor)) {
            panel.appendChild(pickerRow((value) => hooks.apply(editor, value), t("custom"), current, close));
          }
          panel.appendChild(
            menuItem(t("remove"), false, () => {
              hooks.apply(editor, null);
              close();
            }),
          );
          return panel;
        },
      });
      const enable = enabler(hooks, editor, dd.trigger);
      return enable ? { el: dd.el, refresh: enable } : { el: dd.el };
    },
  };
}
