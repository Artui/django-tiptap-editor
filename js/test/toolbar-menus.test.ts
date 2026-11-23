import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import DjangoTipTap from "../src/index";
import type { TipTapConfig } from "../src/default-config";
import type { Editor } from "../src/tiptap-runtime";
import { installPopover, removePopover } from "./popover-stub";

const TOOLBAR = [
  ["fontSize", "fontFamily", "color", "highlight"],
  ["image", "mergeTags", "table"],
];
const CONFIG: TipTapConfig = {
  toolbar: TOOLBAR,
  colorPicker: true,
  imageUploadUrl: "/upload/",
  mergeTags: [
    { label: "First name", value: "{{first}}" },
    { label: "Last name", value: "{{last}}" },
  ],
};
const STYLED = '<p><span style="font-size: 24px; color: #e03e2d">big</span> text</p>';

interface Mounted {
  editor: Editor;
  shell: HTMLElement;
  outside: HTMLButtonElement;
}

let seq = 0;
const mounted: string[] = [];

function mount(content = STYLED, config: TipTapConfig = CONFIG): Mounted {
  const textarea = document.createElement("textarea");
  textarea.id = `menus-${++seq}`;
  textarea.value = content;
  const outside = document.createElement("button");
  document.body.append(textarea, outside);
  const editor = DjangoTipTap.init(textarea, config);
  mounted.push(textarea.id);
  editor.commands.setTextSelection(2);
  const shell = textarea.nextElementSibling as HTMLElement;
  return { editor, shell, outside };
}

function trigger(shell: HTMLElement, label: string): HTMLButtonElement {
  const el = shell.querySelector<HTMLButtonElement>(
    `.django-tiptap__dropdown-trigger[aria-label^="${label}"]`,
  );
  if (!el) {
    throw new Error(`no trigger ${label}`);
  }
  return el;
}

function panel(): HTMLElement | null {
  return document.querySelector<HTMLElement>(".django-tiptap__panel");
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

function click(target: Element, detail: number): void {
  target.dispatchEvent(new MouseEvent("click", { detail, bubbles: true, cancelable: true }));
}

function key(target: Element, name: string, shiftKey = false): KeyboardEvent {
  const event = new KeyboardEvent("keydown", {
    key: name,
    shiftKey,
    bubbles: true,
    cancelable: true,
    composed: true,
  });
  target.dispatchEvent(event);
  return event;
}

// The editor's focus command lands on the next animation frame.
const frame = (): Promise<void> => new Promise((resolve) => requestAnimationFrame(() => resolve()));

function active(): Element | null {
  return document.activeElement;
}

// jsdom's Range has no geometry, and the editor's focus command scrolls the caret into view.
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
  for (const id of mounted.splice(0)) {
    DjangoTipTap.destroy(id);
  }
  document.body.innerHTML = "";
  vi.restoreAllMocks();
  removePopover();
  delete (document as Partial<Document>).execCommand;
});

describe.each(["popover", "portal"])("on the %s path", (path) => {
  beforeEach(() => {
    if (path === "popover") {
      installPopover();
    }
  });

  describe("aria-haspopup names the popup", () => {
    it.each([
      ["Font size", "menu"],
      ["Font family", "menu"],
      ["Insert image", "menu"],
      ["Merge tags", "menu"],
      ["Table", "menu"],
      ["Text color", "dialog"],
      ["Highlight", "dialog"],
    ])("%s is %s", (label, popup) => {
      const { shell } = mount();
      expect(trigger(shell, label).getAttribute("aria-haspopup")).toBe(popup);
    });
  });

  describe("font size and family are menus of radio items", () => {
    it("a keyboard click opens a labelled menu and focuses the checked item", () => {
      const { shell } = mount();
      click(trigger(shell, "Font size"), 0);
      const menu = panel()!.querySelector("[role=menu]")!;
      expect(menu.getAttribute("aria-label")).toBe("Font size");
      expect(items().map((node) => node.getAttribute("role"))).toEqual(
        Array(8).fill("menuitemradio"),
      );
      expect(item("24").getAttribute("aria-checked")).toBe("true");
      expect(items().filter((node) => node.getAttribute("aria-checked") === "true")).toHaveLength(1);
      expect(active()).toBe(item("24"));
    });

    it("ArrowDown on the trigger opens it and focuses the checked item", () => {
      const { shell } = mount();
      const event = key(trigger(shell, "Font size"), "ArrowDown");
      expect(event.defaultPrevented).toBe(true);
      expect(trigger(shell, "Font size").getAttribute("aria-expanded")).toBe("true");
      expect(active()).toBe(item("24"));
    });

    it("checks Default when no value is set", () => {
      const { shell } = mount("<p>plain</p>");
      click(trigger(shell, "Font family"), 0);
      expect(item("Default").getAttribute("aria-checked")).toBe("true");
      expect(active()).toBe(item("Default"));
    });

    it("ArrowDown and ArrowUp wrap, Home and End go to the ends", () => {
      const { shell } = mount();
      click(trigger(shell, "Font size"), 0);
      expect(key(item("24"), "ArrowDown").defaultPrevented).toBe(true);
      expect(active()).toBe(item("30"));
      key(item("30"), "End");
      expect(active()).toBe(item("36"));
      key(item("36"), "ArrowDown");
      expect(active()).toBe(item("Default"));
      key(item("Default"), "ArrowUp");
      expect(active()).toBe(item("36"));
      key(item("36"), "Home");
      expect(active()).toBe(item("Default"));
    });

    it("a printable key moves to the next item starting with it", () => {
      const { shell } = mount();
      click(trigger(shell, "Font size"), 0);
      key(item("24"), "3");
      expect(active()).toBe(item("30"));
      key(item("30"), "3");
      expect(active()).toBe(item("36"));
      expect(key(item("36"), "z").defaultPrevented).toBe(false);
      expect(active()).toBe(item("36"));
    });

    it("ignores a printable key held with Ctrl, Meta or Alt", () => {
      const { shell } = mount();
      click(trigger(shell, "Font size"), 0);
      for (const mod of ["ctrlKey", "metaKey", "altKey"]) {
        const event = new KeyboardEvent("keydown", { key: "3", bubbles: true, cancelable: true, [mod]: true });
        item("24").dispatchEvent(event);
        expect(event.defaultPrevented).toBe(false);
        expect(active()).toBe(item("24"));
      }
    });

    it("leaves Left, Right and Enter alone", () => {
      const { shell } = mount();
      click(trigger(shell, "Font size"), 0);
      expect(key(item("24"), "ArrowLeft").defaultPrevented).toBe(false);
      expect(key(item("24"), "ArrowRight").defaultPrevented).toBe(false);
      expect(key(item("24"), "Enter").defaultPrevented).toBe(false);
      expect(active()).toBe(item("24"));
    });

    it("keeps exactly one item at tabindex 0 as focus moves", () => {
      const { shell } = mount();
      click(trigger(shell, "Font size"), 0);
      const zero = (): HTMLElement[] => items().filter((node) => node.tabIndex === 0);
      expect(zero()).toEqual([item("24")]);
      key(item("24"), "ArrowDown");
      expect(zero()).toEqual([item("30")]);
      item("12").focus();
      expect(zero()).toEqual([item("12")]);
    });

    it("Tab from any item closes the menu and moves to the next control", () => {
      const { shell } = mount();
      const button = trigger(shell, "Font size");
      click(button, 0);
      key(item("24"), "ArrowDown");
      const event = key(item("30"), "Tab");
      expect(event.defaultPrevented).toBe(true);
      expect(panel()).toBeNull();
      expect(button.getAttribute("aria-expanded")).toBe("false");
      expect(active()).toBe(trigger(shell, "Font family"));
    });

    it("Shift+Tab closes the menu and focuses the trigger", () => {
      const { shell } = mount();
      const button = trigger(shell, "Font size");
      click(button, 0);
      key(item("24"), "ArrowDown");
      expect(key(item("30"), "Tab", true).defaultPrevented).toBe(true);
      expect(panel()).toBeNull();
      expect(button.getAttribute("aria-expanded")).toBe("false");
      expect(active()).toBe(button);
    });

    it("Escape detaches the panel and focuses the trigger", () => {
      const { shell } = mount();
      const button = trigger(shell, "Font size");
      click(button, 0);
      key(active()!, "Escape");
      expect(panel()).toBeNull();
      expect(button.getAttribute("aria-expanded")).toBe("false");
      expect(active()).toBe(button);
    });

    it("a pick applies the value, closes, and leaves focus in the editor", async () => {
      const { shell, editor } = mount();
      const button = trigger(shell, "Font size");
      click(button, 0);
      click(item("30"), 0);
      await frame();
      expect(editor.getAttributes("textStyle").fontSize).toBe("30px");
      expect(panel()).toBeNull();
      expect(button.getAttribute("aria-expanded")).toBe("false");
      expect(active()).toBe(editor.view.dom);
    });
  });

  describe("image, merge tags and table are menus of actions", () => {
    it("a keyboard open focuses the first item, an ArrowUp open the last", () => {
      const { shell } = mount();
      const button = trigger(shell, "Insert image");
      click(button, 0);
      expect(panel()!.querySelector("[role=menu]")?.getAttribute("aria-label")).toBe("Insert image");
      expect(items().map((node) => node.getAttribute("role"))).toEqual(["menuitem", "menuitem"]);
      expect(active()).toBe(item("Insert by URL"));
      key(active()!, "Escape");
      key(button, "ArrowUp");
      expect(active()).toBe(item("Upload…"));
    });

    it("an item takes a keyboard click, runs, closes and returns focus to the editor", async () => {
      const { shell, editor } = mount();
      const button = trigger(shell, "Merge tags");
      click(button, 0);
      expect(active()).toBe(item("First name"));
      key(item("First name"), "ArrowDown");
      click(item("Last name"), 0);
      await frame();
      expect(editor.getHTML()).toContain("{{last}}");
      expect(panel()).toBeNull();
      expect(button.getAttribute("aria-expanded")).toBe("false");
      expect(active()).toBe(editor.view.dom);
    });

    it("Shift+Tab from an item closes the menu and focuses the trigger", () => {
      const { shell } = mount();
      const button = trigger(shell, "Table");
      click(button, 0);
      expect(key(item("Insert table"), "Tab", true).defaultPrevented).toBe(true);
      expect(panel()).toBeNull();
      expect(active()).toBe(button);
    });

    it("inside a table the groups are divided by separators", () => {
      const { shell } = mount(
        "<table><tbody><tr><td><p>a</p></td><td><p>b</p></td></tr></tbody></table>",
      );
      click(trigger(shell, "Table"), 0);
      const seps = panel()!.querySelectorAll(".django-tiptap__sep");
      expect(seps.length).toBeGreaterThan(0);
      for (const sep of Array.from(seps)) {
        expect(sep.getAttribute("role")).toBe("separator");
      }
      key(item("Insert table"), "End");
      expect(active()).toBe(items()[items().length - 1]);
    });

    it("ArrowDown steps over a separator to the next item", () => {
      const { shell } = mount(
        "<table><tbody><tr><td><p>a</p></td><td><p>b</p></td></tr></tbody></table>",
      );
      click(trigger(shell, "Table"), 0);
      key(item("Insert table"), "ArrowDown");
      expect(active()).toBe(item("Add row above"));
    });

    it("one checkbox item adds the table's lines, and then removes them", async () => {
      const { shell, editor } = mount(
        "<table><tbody><tr><td><p>a</p></td><td><p>b</p></td></tr></tbody></table>",
      );
      click(trigger(shell, "Table"), 0);
      expect(item("Table lines").getAttribute("aria-checked")).toBe("false");
      click(item("Table lines"), 0);
      await frame();
      expect(editor.getJSON().content?.[0].attrs?.border).toBe("1px solid #d0d5dd");
      editor.commands.setTextSelection(3);
      click(trigger(shell, "Table"), 0);
      expect(item("Table lines").getAttribute("aria-checked")).toBe("true");
      click(item("Table lines"), 0);
      await frame();
      expect(editor.getHTML()).not.toContain("border");
    });

    it("a named key such as Delete is not typeahead", () => {
      const { shell } = mount(
        "<table><tbody><tr><td><p>a</p></td><td><p>b</p></td></tr></tbody></table>",
      );
      click(trigger(shell, "Table"), 0);
      expect(key(item("Insert table"), "Delete").defaultPrevented).toBe(false);
      expect(active()).toBe(item("Insert table"));
    });

    it("a mouse-opened action menu has exactly one tabbable item, the first", () => {
      const { shell } = mount();
      click(trigger(shell, "Insert image"), 1);
      expect(items().filter((node) => node.tabIndex === 0)).toEqual([item("Insert by URL")]);
    });

    it("Insert by URL with the prompt cancelled leaves focus in the editor", async () => {
      vi.spyOn(window, "prompt").mockReturnValue(null);
      const { shell, editor } = mount();
      click(trigger(shell, "Insert image"), 0);
      click(item("Insert by URL"), 0);
      expect(window.prompt).toHaveBeenCalled();
      expect(panel()).toBeNull();
      await frame();
      expect(active()).toBe(editor.view.dom);
    });

    it("a keyboard pick moves focus straight to the editor, never via the trigger", async () => {
      const { shell, editor } = mount();
      click(trigger(shell, "Font size"), 0);
      const seen: Element[] = [];
      const record = (event: Event): void => void seen.push(event.target as Element);
      document.addEventListener("focusin", record);
      click(item("30"), 0);
      await frame();
      document.removeEventListener("focusin", record);
      expect(seen).not.toContain(trigger(shell, "Font size"));
      expect(active()).toBe(editor.view.dom);
    });

    it("a pick leaves focus where the command put it outside the panel", async () => {
      const { shell, outside } = mount();
      vi.spyOn(window, "prompt").mockImplementation(() => {
        outside.focus();
        return null;
      });
      click(trigger(shell, "Insert image"), 0);
      click(item("Insert by URL"), 0);
      await frame();
      expect(active()).toBe(outside);
    });

    it("a pick whose command drops focus to the body puts it in the editor", async () => {
      const { shell, editor } = mount();
      vi.spyOn(window, "prompt").mockImplementation(() => {
        (document.activeElement as HTMLElement).blur();
        return null;
      });
      click(trigger(shell, "Insert image"), 0);
      click(item("Insert by URL"), 0);
      await frame();
      expect(active()).toBe(editor.view.dom);
    });

    it("in a shadow root, a pick whose command drops focus puts it in the editor", async () => {
      // jsdom reports Safari, whose shadow-root selection path in ProseMirror needs execCommand.
      Object.defineProperty(document, "execCommand", { value: () => false, configurable: true });
      const host = document.createElement("div");
      document.body.appendChild(host);
      const root = host.attachShadow({ mode: "open" });
      const textarea = document.createElement("textarea");
      textarea.id = `menus-${++seq}`;
      root.appendChild(textarea);
      const editor = DjangoTipTap.init(textarea, CONFIG);
      mounted.push(textarea.id);
      vi.spyOn(window, "prompt").mockImplementation(() => {
        (root.activeElement as HTMLElement).blur();
        return null;
      });
      const shell = textarea.nextElementSibling as HTMLElement;
      const button = trigger(shell, "Insert image");
      button.focus();
      click(button, 0);
      const first = root.querySelector<HTMLElement>("[role=menuitem]")!;
      expect(root.activeElement).toBe(first);
      click(first, 0);
      await frame();
      expect(root.activeElement).toBe(editor.view.dom);
    });

    it("an empty merge-tag panel is no menu and leaves focus on the trigger", () => {
      const { shell } = mount(STYLED, { ...CONFIG, mergeTags: [] });
      const button = trigger(shell, "Merge tags");
      button.focus();
      click(button, 0);
      expect(panel()).not.toBeNull();
      expect(panel()!.querySelector("[role=menu]")).toBeNull();
      expect(active()).toBe(button);
    });
  });

  describe("colour panels are dialogs", () => {
    it("is a labelled dialog whose current swatch is pressed", () => {
      const { shell } = mount();
      click(trigger(shell, "Text color"), 0);
      const dialog = panel()!.querySelector("[role=dialog]")!;
      expect(dialog.getAttribute("aria-label")).toBe("Text color");
      const swatches = Array.from(dialog.querySelectorAll<HTMLElement>(".django-tiptap__swatch"));
      expect(swatches.filter((sw) => sw.getAttribute("aria-pressed") === "true")).toEqual([
        dialog.querySelector('[aria-label="#e03e2d"]'),
      ]);
      expect(swatches.filter((sw) => sw.getAttribute("aria-pressed") === "false")).toHaveLength(
        swatches.length - 1,
      );
      expect(active()).toBe(dialog.querySelector('[aria-label="#e03e2d"]'));
      const remove = Array.from(dialog.querySelectorAll("button")).find(
        (node) => node.textContent === "Remove",
      )!;
      expect(remove.hasAttribute("role")).toBe(false);
      expect(dialog.querySelector("[role^=menu]")).toBeNull();
    });

    it("a keyboard open with no colour set focuses the first swatch", () => {
      const { shell } = mount("<p>plain</p>");
      click(trigger(shell, "Highlight"), 0);
      expect(active()).toBe(panel()!.querySelector(".django-tiptap__swatch"));
    });

    it("Shift+Tab off the first control focuses the trigger and leaves it open", () => {
      const { shell } = mount("<p>plain</p>");
      const button = trigger(shell, "Highlight");
      click(button, 0);
      expect(key(active()!, "Tab", true).defaultPrevented).toBe(true);
      expect(active()).toBe(button);
      expect(panel()).not.toBeNull();
      expect(button.getAttribute("aria-expanded")).toBe("true");
    });

    it("focus moving to an outside node closes it; relatedTarget null does not", () => {
      const { shell, outside } = mount();
      const button = trigger(shell, "Text color");
      click(button, 0);
      const swatch = active()!;
      swatch.dispatchEvent(new FocusEvent("focusout", { bubbles: true, relatedTarget: null }));
      expect(panel()).not.toBeNull();
      swatch.dispatchEvent(new FocusEvent("focusout", { bubbles: true, relatedTarget: button }));
      expect(panel()).not.toBeNull();
      const next = swatch.nextElementSibling!;
      swatch.dispatchEvent(new FocusEvent("focusout", { bubbles: true, relatedTarget: next }));
      expect(panel()).not.toBeNull();
      outside.focus();
      swatch.dispatchEvent(new FocusEvent("focusout", { bubbles: true, relatedTarget: outside }));
      expect(panel()).toBeNull();
      expect(button.getAttribute("aria-expanded")).toBe("false");
      expect(active()).toBe(outside);
    });

    it("a menu has no focusout backstop", () => {
      const { shell, outside } = mount();
      click(trigger(shell, "Font size"), 0);
      active()!.dispatchEvent(new FocusEvent("focusout", { bubbles: true, relatedTarget: outside }));
      expect(panel()).not.toBeNull();
    });
  });

  describe("a mouse open", () => {
    it("leaves focus in the editor, and Escape then leaves it there", async () => {
      const { shell, editor } = mount();
      editor.commands.focus();
      await frame();
      expect(active()).toBe(editor.view.dom);
      const button = trigger(shell, "Font size");
      click(button, 1);
      expect(panel()).not.toBeNull();
      expect(active()).toBe(editor.view.dom);
      key(editor.view.dom, "Escape");
      expect(panel()).toBeNull();
      expect(button.getAttribute("aria-expanded")).toBe("false");
      expect(active()).toBe(editor.view.dom);
    });

    it("the trigger's keydown does not handle Enter or Space", () => {
      const { shell } = mount();
      const button = trigger(shell, "Font size");
      expect(key(button, "Enter").defaultPrevented).toBe(false);
      expect(key(button, " ").defaultPrevented).toBe(false);
      expect(panel()).toBeNull();
    });
  });
});
