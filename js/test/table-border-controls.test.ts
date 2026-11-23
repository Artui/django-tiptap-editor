import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";

import DjangoTipTap from "../src/index";
import { DEFAULT_TOOLBAR } from "../src/default-config";
import type { TipTapConfig } from "../src/default-config";
import { getTranslator } from "../src/i18n";
import type { Editor } from "../src/tiptap-runtime";

const CONTROLS = [["table", "tableBorderColor", "tableBorderWidth"]];
const CONFIG: TipTapConfig = { toolbar: CONTROLS };
const CELLS = "<tbody><tr><td><p>a</p></td><td><p>b</p></td></tr></tbody></table>";
const UNRULED = `<p>out</p><table>${CELLS}`;
const RULED =
  '<p>out</p><table border="1"><tbody><tr><td style="border: 2px solid #1f2329"><p>a</p></td>' +
  "<td><p>b</p></td></tr></tbody></table>";
const DOTTED =
  '<p>out</p><table border="1"><tbody><tr><td style="border: 2px dotted red"><p>a</p></td>' +
  "<td><p>b</p></td></tr></tbody></table>";
const OUTSIDE = 2;
const IN_CELL = 9;

interface Mounted {
  editor: Editor;
  shell: HTMLElement;
  fieldset: HTMLFieldSetElement;
}

let seq = 0;

function mount(content: string, config: TipTapConfig = CONFIG): Mounted {
  const fieldset = document.createElement("fieldset");
  const textarea = document.createElement("textarea");
  textarea.id = `borders-${++seq}`;
  textarea.value = content;
  fieldset.appendChild(textarea);
  document.body.appendChild(fieldset);
  const editor = DjangoTipTap.init(textarea, config);
  editor.commands.setTextSelection(IN_CELL);
  return { editor, shell: textarea.nextElementSibling as HTMLElement, fieldset };
}

function trigger(shell: HTMLElement, key: string): HTMLButtonElement {
  const el = shell.querySelector<HTMLButtonElement>(`[data-key="${key}"] .django-tiptap__dropdown-trigger`);
  if (!el) {
    throw new Error(`no trigger ${key}`);
  }
  return el;
}

function open(shell: HTMLElement, key: string, detail = 1): void {
  trigger(shell, key).dispatchEvent(new MouseEvent("click", { detail, bubbles: true, cancelable: true }));
}

function pick(node: Element): void {
  node.dispatchEvent(new MouseEvent("click", { detail: 1, bubbles: true, cancelable: true }));
}

function items(): HTMLElement[] {
  return Array.from(document.querySelectorAll<HTMLElement>(".django-tiptap__panel [role^=menuitem]"));
}

function item(label: string): HTMLElement {
  const found = items().find((node) => node.textContent?.trim() === label);
  if (!found) {
    throw new Error(`no item ${label}`);
  }
  return found;
}

function swatches(): HTMLButtonElement[] {
  return Array.from(document.querySelectorAll<HTMLButtonElement>(".django-tiptap__panel .django-tiptap__swatch"));
}

function swatch(color: string): HTMLButtonElement {
  const found = swatches().find((node) => node.title === color);
  if (!found) {
    throw new Error(`no swatch ${color}`);
  }
  return found;
}

function remove(): HTMLElement {
  const found = Array.from(document.querySelectorAll<HTMLElement>(".django-tiptap__panel .django-tiptap__menu-item")).find(
    (node) => node.textContent === "Remove",
  );
  if (!found) {
    throw new Error("no Remove");
  }
  return found;
}

function border(editor: Editor): unknown {
  return editor.getJSON().content?.[1].attrs?.border;
}

function disabled(shell: HTMLElement): [boolean, boolean] {
  return [trigger(shell, "tableBorderColor").disabled, trigger(shell, "tableBorderWidth").disabled];
}

const settle = (): Promise<void> => new Promise((resolve) => setTimeout(resolve, 0));

const EMPTY_RECT = { top: 0, bottom: 0, left: 0, right: 0, width: 0, height: 0, x: 0, y: 0 };
const { getClientRects, getBoundingClientRect } = Range.prototype;
beforeAll(() => {
  Range.prototype.getClientRects = () => [] as unknown as DOMRectList;
  Range.prototype.getBoundingClientRect = () => EMPTY_RECT as DOMRect;
});
afterAll(() => {
  Object.assign(Range.prototype, { getClientRects, getBoundingClientRect });
});

afterEach(() => {
  document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
  for (const textarea of document.querySelectorAll("textarea")) {
    DjangoTipTap.destroy(textarea.id);
  }
  document.body.innerHTML = "";
});

describe("the table menu's Table lines item", () => {
  it("is a menuitemcheckbox that toggles the table's lines both ways", () => {
    const { editor, shell } = mount(UNRULED);
    open(shell, "table");
    const lines = item("Table lines");
    expect(lines.getAttribute("role")).toBe("menuitemcheckbox");
    expect(lines.getAttribute("aria-checked")).toBe("false");
    expect(lines.classList.contains("is-active")).toBe(false);
    pick(lines);
    expect(border(editor)).toBe("1px solid #d0d5dd");
    editor.commands.setTextSelection(IN_CELL);
    open(shell, "table");
    expect(item("Table lines").getAttribute("aria-checked")).toBe("true");
    expect(item("Table lines").classList.contains("is-active")).toBe(true);
    pick(item("Table lines"));
    expect(border(editor)).toBeNull();
    expect(editor.getHTML()).not.toContain("border");
  });

  it("leaves the other entries plain menuitems", () => {
    const { shell } = mount(RULED);
    open(shell, "table");
    const roles = items().map((node) => node.getAttribute("role"));
    expect(roles.filter((role) => role === "menuitemcheckbox")).toHaveLength(1);
    expect(roles.filter((role) => role === "menuitem")).toHaveLength(8);
  });

  it("a keyboard open in a ruled table still focuses the first item, an ArrowUp open the last", () => {
    const { shell } = mount(RULED);
    open(shell, "table", 0);
    expect(document.activeElement).toBe(item("Insert table"));
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    trigger(shell, "table").dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowUp", bubbles: true, cancelable: true }),
    );
    expect(document.activeElement).toBe(item("Delete table"));
  });

  it("a mouse open in a ruled table leaves the first item the one tabbable", () => {
    const { shell } = mount(RULED);
    open(shell, "table");
    expect(items().filter((node) => node.tabIndex === 0)).toEqual([item("Insert table")]);
  });

  it("is reached by the arrow keys like every other item", () => {
    const { shell } = mount(RULED);
    open(shell, "table", 0);
    item("Add column right").dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true, cancelable: true }),
    );
    expect(document.activeElement).toBe(item("Table lines"));
    expect(item("Table lines").tabIndex).toBe(0);
  });
});

describe("the table line controls", () => {
  it("sit right after table in the default toolbar", () => {
    const group = DEFAULT_TOOLBAR.find((keys) => keys.includes("table"));
    expect(group?.slice(group.indexOf("table"))).toEqual(["table", "tableBorderColor", "tableBorderWidth"]);
  });

  it("need the table feature", () => {
    const { shell } = mount("<p>a</p>", { toolbar: CONTROLS, features: ["bold"] });
    expect(shell.querySelector('[data-key="tableBorderColor"], [data-key="tableBorderWidth"]')).toBeNull();
  });

  it("are titled in en and sv", () => {
    const en = getTranslator("en");
    const sv = getTranslator("sv");
    expect(["tableLines", "tableBorderColor", "tableBorderWidth"].map((k) => en(k))).toEqual([
      "Table lines",
      "Table line colour",
      "Table line width",
    ]);
    expect(["tableLines", "tableBorderColor", "tableBorderWidth"].map((k) => sv(k))).toEqual([
      "Tabellinjer",
      "Tabellinjefärg",
      "Tabellinjebredd",
    ]);
  });

  it("are disabled outside a table and in an unruled one, enabled in a ruled one", () => {
    const unruled = mount(UNRULED);
    expect(disabled(unruled.shell)).toEqual([true, true]);
    const ruled = mount(RULED);
    expect(disabled(ruled.shell)).toEqual([false, false]);
    ruled.editor.commands.setTextSelection(OUTSIDE);
    expect(disabled(ruled.shell)).toEqual([true, true]);
    ruled.editor.commands.setTextSelection(IN_CELL);
    expect(disabled(ruled.shell)).toEqual([false, false]);
  });

  it("are disabled outside a ruled table with a toolbarLabels label too", () => {
    const labels = { tableBorderColor: "Colour", tableBorderWidth: "Width" };
    const { editor, shell } = mount(RULED, { ...CONFIG, toolbarLabels: labels });
    expect(disabled(shell)).toEqual([false, false]);
    editor.commands.setTextSelection(OUTSIDE);
    expect(disabled(shell)).toEqual([true, true]);
  });

  it("follow the table menu's toggle", () => {
    const { shell } = mount(UNRULED);
    open(shell, "table");
    pick(item("Table lines"));
    expect(disabled(shell)).toEqual([false, false]);
  });

  it("are disabled while the editor is locked, and come back as the table says", async () => {
    const { editor, shell, fieldset } = mount(RULED);
    fieldset.disabled = true;
    await settle();
    expect(disabled(shell)).toEqual([true, true]);
    fieldset.disabled = false;
    await settle();
    expect(disabled(shell)).toEqual([false, false]);
    editor.commands.setTextSelection(OUTSIDE);
    fieldset.disabled = true;
    await settle();
    fieldset.disabled = false;
    await settle();
    expect(disabled(shell)).toEqual([true, true]);
  });
});

describe("the table line colour control", () => {
  it("is a dialog of the default swatches with the table's colour pressed", () => {
    const { shell } = mount(RULED);
    expect(trigger(shell, "tableBorderColor").getAttribute("aria-haspopup")).toBe("dialog");
    open(shell, "tableBorderColor");
    expect(document.querySelector(".django-tiptap__panel [role=dialog]")?.getAttribute("aria-label")).toBe(
      "Table line colour",
    );
    expect(swatches().map((node) => node.title)).toEqual(["#d0d5dd", "#858b97", "#5c6370", "#1f2329", "#000000"]);
    expect(swatches().map((node) => node.getAttribute("aria-pressed"))).toEqual([
      "false",
      "false",
      "false",
      "true",
      "false",
    ]);
    expect(document.querySelector(".django-tiptap__panel input[type=color]")).toBeNull();
  });

  it("takes its swatches from tableBorderColors", () => {
    const { shell } = mount(RULED, { ...CONFIG, tableBorderColors: ["#123456", "#abcdef"] });
    open(shell, "tableBorderColor");
    expect(swatches().map((node) => node.title)).toEqual(["#123456", "#abcdef"]);
  });

  it("a pick keeps the width", () => {
    const { editor, shell } = mount(RULED);
    open(shell, "tableBorderColor");
    pick(swatch("#000000"));
    expect(border(editor)).toBe("2px solid #000000");
    expect(editor.getJSON().content?.[1].content?.[0].content?.[1].attrs?.border).toBe("2px solid #000000");
    expect(editor.getHTML()).not.toContain("<span");
  });

  it("Remove takes the lines off", () => {
    const { editor, shell } = mount(RULED);
    open(shell, "tableBorderColor");
    pick(remove());
    expect(border(editor)).toBeNull();
    expect(disabled(shell)).toEqual([true, true]);
  });

  it("with colorPicker, the custom colour keeps the width and sets no text colour", () => {
    const { editor, shell } = mount(RULED, { ...CONFIG, colorPicker: true });
    open(shell, "tableBorderColor");
    const input = document.querySelector<HTMLInputElement>(".django-tiptap__panel input[type=color]");
    expect(input?.value).toBe("#1f2329");
    input!.value = "#112233";
    input!.dispatchEvent(new Event("change", { bubbles: true }));
    expect(border(editor)).toBe("2px solid #112233");
    expect(editor.getHTML()).not.toContain("<span");
  });
});

describe("the table line width control", () => {
  it("is a radio menu of the default widths, no Default, the table's width checked", () => {
    const { shell } = mount(RULED);
    expect(trigger(shell, "tableBorderWidth").getAttribute("aria-haspopup")).toBe("menu");
    open(shell, "tableBorderWidth");
    expect(items().map((node) => [node.textContent, node.getAttribute("role"), node.getAttribute("aria-checked")])).toEqual([
      ["1", "menuitemradio", "false"],
      ["2", "menuitemradio", "true"],
      ["3", "menuitemradio", "false"],
    ]);
  });

  it("shows the table's width on its trigger", () => {
    const { editor, shell } = mount(RULED);
    const button = trigger(shell, "tableBorderWidth");
    expect(button.querySelector(".django-tiptap__value-text")?.textContent).toBe("2");
    expect(button.getAttribute("aria-label")).toBe("Table line width: 2");
    const sizer = button.querySelector(".django-tiptap__value-sizer");
    expect(Array.from(sizer?.children ?? []).map((node) => node.textContent)).toEqual(["1", "2", "3"]);
    open(shell, "tableBorderWidth");
    pick(item("3"));
    expect(button.querySelector(".django-tiptap__value-text")?.textContent).toBe("3");
    editor.commands.setTextSelection(IN_CELL);
    expect(button.getAttribute("aria-label")).toBe("Table line width: 3");
  });

  it("takes its widths from tableBorderWidths", () => {
    const { shell } = mount(RULED, { ...CONFIG, tableBorderWidths: ["4px", "8px"] });
    open(shell, "tableBorderWidth");
    expect(items().map((node) => node.textContent)).toEqual(["4", "8"]);
  });

  it("a pick keeps the colour", () => {
    const { editor, shell } = mount(RULED);
    open(shell, "tableBorderWidth");
    pick(item("3"));
    expect(border(editor)).toBe("3px solid #1f2329");
    expect(editor.getHTML()).not.toContain("<span");
  });
});

describe("a border that is not <width> solid <colour>", () => {
  it("reads as 1px and #d0d5dd, and a pick writes a solid border", () => {
    const { editor, shell } = mount(DOTTED);
    expect(border(editor)).toBe("2px dotted red");
    open(shell, "tableBorderColor");
    expect(swatch("#d0d5dd").getAttribute("aria-pressed")).toBe("true");
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    open(shell, "tableBorderWidth");
    expect(item("1").getAttribute("aria-checked")).toBe("true");
    pick(item("3"));
    expect(border(editor)).toBe("3px solid #d0d5dd");
  });
});
