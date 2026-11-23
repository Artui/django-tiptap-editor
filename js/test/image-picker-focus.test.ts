// The Library picker is a modal dialog: opening it from the Image menu puts focus inside
// it, Tab stays inside, and every way of closing it returns focus to the editor.
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import DjangoTipTap from "../src/index";
import type { TipTapConfig } from "../src/default-config";
import type { Editor } from "../src/tiptap-runtime";
import { installDialog, removeDialog } from "./dialog-stub";
import { installPopover, removePopover } from "./popover-stub";

const CONFIG: TipTapConfig = { toolbar: [["image"]], imageListUrl: "/images/" };
const ITEMS = [
  { title: "Cat", value: "https://example.com/cat.png" },
  { title: "Dog", value: "https://example.com/dog.png" },
];

let seq = 0;
const mounted: string[] = [];

function mount(): { editor: Editor; shell: HTMLElement } {
  const textarea = document.createElement("textarea");
  textarea.id = `picker-${++seq}`;
  textarea.value = "<p>text</p>";
  document.body.append(textarea);
  const editor = DjangoTipTap.init(textarea, CONFIG);
  mounted.push(textarea.id);
  return { editor, shell: textarea.nextElementSibling as HTMLElement };
}

function click(target: Element, detail = 0): void {
  target.dispatchEvent(new MouseEvent("click", { detail, bubbles: true, cancelable: true }));
}

function key(target: Element, name: string, shiftKey = false): KeyboardEvent {
  const event = new KeyboardEvent("keydown", { key: name, shiftKey, bubbles: true, cancelable: true });
  target.dispatchEvent(event);
  return event;
}

const frame = (): Promise<void> => new Promise((resolve) => requestAnimationFrame(() => resolve()));
const settle = async (): Promise<void> => {
  for (let i = 0; i < 5; i++) {
    await Promise.resolve();
  }
  await frame();
};

function overlay(): HTMLElement | null {
  return document.querySelector<HTMLElement>(".django-tiptap__modal-overlay");
}
function closeButton(): HTMLElement {
  return document.querySelector<HTMLElement>(".django-tiptap__modal-close") as HTMLElement;
}
function tiles(): HTMLElement[] {
  return Array.from(document.querySelectorAll<HTMLElement>(".django-tiptap__picker-item"));
}

// Opens the picker the way a keyboard user does: Enter on the trigger, Enter on the item.
async function openFromKeyboard(shell: HTMLElement): Promise<void> {
  const trigger = shell.querySelector(
    '.django-tiptap__dropdown-trigger[aria-label^="Insert image"]',
  ) as HTMLElement;
  click(trigger);
  const library = Array.from(document.querySelectorAll(".django-tiptap__panel [role=menuitem]")).find(
    (node) => node.textContent?.trim() === "From library…",
  ) as HTMLElement;
  click(library);
  await frame();
}

let resolveFetch: (items: unknown) => void = () => {};

const EMPTY_RECT = { top: 0, bottom: 0, left: 0, right: 0, width: 0, height: 0, x: 0, y: 0 };
const { getClientRects, getBoundingClientRect } = Range.prototype;
beforeAll(() => {
  Range.prototype.getClientRects = () => [] as unknown as DOMRectList;
  Range.prototype.getBoundingClientRect = () => EMPTY_RECT as DOMRect;
});
afterAll(() => {
  Object.assign(Range.prototype, { getClientRects, getBoundingClientRect });
});

beforeEach(() => {
  installPopover();
  installDialog();
  vi.stubGlobal(
    "fetch",
    vi.fn(
      () =>
        new Promise((resolve) => {
          resolveFetch = (items) => resolve({ json: () => Promise.resolve(items) });
        }),
    ),
  );
});

afterEach(() => {
  for (const id of mounted.splice(0)) {
    DjangoTipTap.destroy(id);
  }
  document.body.innerHTML = "";
  vi.unstubAllGlobals();
  removePopover();
  removeDialog();
});

describe("opening the library picker from the keyboard", () => {
  it("focuses the close button while the list loads", async () => {
    const { shell } = mount();
    await openFromKeyboard(shell);
    expect(document.activeElement).toBe(closeButton());
    expect(overlay()?.contains(document.activeElement)).toBe(true);
  });

  it("then focuses the first tile once the list arrives", async () => {
    const { shell } = mount();
    await openFromKeyboard(shell);
    resolveFetch(ITEMS);
    await settle();
    expect(document.activeElement).toBe(tiles()[0]);
  });

  it("keeps focus on the close button for an empty list", async () => {
    const { shell } = mount();
    await openFromKeyboard(shell);
    resolveFetch([]);
    await settle();
    expect(document.activeElement).toBe(closeButton());
  });
});

describe("the picker is a labelled modal dialog", () => {
  it("is an open native dialog with aria-modal and its heading as name", async () => {
    const { shell } = mount();
    await openFromKeyboard(shell);
    const dialog = overlay() as HTMLElement;
    expect(dialog.matches("dialog[open]")).toBe(true);
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    const labelledBy = dialog.getAttribute("aria-labelledby") ?? "";
    expect(document.getElementById(labelledBy)?.textContent).toBe("Select an image");
  });

  it("gives each open picker its own heading id", async () => {
    const first = mount();
    const second = mount();
    await openFromKeyboard(first.shell);
    await openFromKeyboard(second.shell);
    const ids = Array.from(document.querySelectorAll(".django-tiptap__modal-overlay")).map((el) =>
      el.getAttribute("aria-labelledby"),
    );
    expect(ids).toHaveLength(2);
    expect(new Set(ids).size).toBe(2);
  });
});

describe("Tab stays inside the picker", () => {
  it("wraps from the last tile to the close button and back", async () => {
    const { shell } = mount();
    await openFromKeyboard(shell);
    resolveFetch(ITEMS);
    await settle();
    const last = tiles()[1];
    last.focus();
    expect(key(last, "Tab").defaultPrevented).toBe(true);
    expect(document.activeElement).toBe(closeButton());
    expect(key(closeButton(), "Tab", true).defaultPrevented).toBe(true);
    expect(document.activeElement).toBe(last);
  });

  it("leaves Tab between inner stops to the browser", async () => {
    const { shell } = mount();
    await openFromKeyboard(shell);
    resolveFetch(ITEMS);
    await settle();
    expect(key(tiles()[0], "Tab").defaultPrevented).toBe(false);
    expect(key(tiles()[0], "Tab", true).defaultPrevented).toBe(false);
    expect(key(tiles()[0], "Enter").defaultPrevented).toBe(false);
  });

  it("lets Enter through on the last stop", async () => {
    const { shell } = mount();
    await openFromKeyboard(shell);
    resolveFetch(ITEMS);
    await settle();
    tiles()[1].focus();
    expect(key(tiles()[1], "Enter").defaultPrevented).toBe(false);
  });

  it("wraps Shift+Tab to the last stop from the dialog itself (a press on its heading)", async () => {
    const { shell } = mount();
    await openFromKeyboard(shell);
    resolveFetch(ITEMS);
    await settle();
    const dialog = overlay() as HTMLElement;
    dialog.tabIndex = -1;
    dialog.focus();
    expect(key(dialog, "Tab", true).defaultPrevented).toBe(true);
    expect(document.activeElement).toBe(tiles()[1]);
  });

  it("holds focus on the close button when it is the only stop", async () => {
    const { shell } = mount();
    await openFromKeyboard(shell);
    expect(key(closeButton(), "Tab").defaultPrevented).toBe(true);
    expect(document.activeElement).toBe(closeButton());
  });
});

describe("every close path returns focus to the editor", () => {
  const paths: [string, () => void][] = [
    ["Escape (cancel)", () => overlay()?.dispatchEvent(new Event("cancel", { cancelable: true }))],
    ["the close button", () => closeButton().click()],
    [
      "a click on the backdrop",
      () => overlay()?.dispatchEvent(new MouseEvent("mousedown", { bubbles: true })),
    ],
    ["picking a tile", () => tiles()[0].click()],
  ];

  it.each(paths)("%s", async (_name, act) => {
    const { shell, editor } = mount();
    await openFromKeyboard(shell);
    resolveFetch(ITEMS);
    await settle();
    act();
    expect(overlay()).toBeNull();
    expect(document.activeElement).toBe(editor.view.dom);
  });

  it("Escape's cancel is prevented so the picker tears itself down", async () => {
    const { shell } = mount();
    await openFromKeyboard(shell);
    const cancel = new Event("cancel", { cancelable: true });
    overlay()?.dispatchEvent(cancel);
    expect(cancel.defaultPrevented).toBe(true);
  });

  it("picking a tile inserts its image", async () => {
    const { shell, editor } = mount();
    await openFromKeyboard(shell);
    resolveFetch(ITEMS);
    await settle();
    tiles()[1].click();
    expect(editor.getHTML()).toContain('src="https://example.com/dog.png"');
  });

  it("a press on the backdrop keeps its default focus change from undoing the return", async () => {
    const { shell } = mount();
    await openFromKeyboard(shell);
    const press = new MouseEvent("mousedown", { bubbles: true, cancelable: true });
    overlay()?.dispatchEvent(press);
    expect(press.defaultPrevented).toBe(true);
  });

  it("a press inside the box does not close it", async () => {
    const { shell } = mount();
    await openFromKeyboard(shell);
    const box = document.querySelector(".django-tiptap__modal") as HTMLElement;
    box.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    expect(overlay()).not.toBeNull();
  });

  it("closing before the list arrives moves no focus into a removed dialog", async () => {
    const { shell, editor } = mount();
    await openFromKeyboard(shell);
    closeButton().click();
    resolveFetch(ITEMS);
    await settle();
    expect(document.activeElement).toBe(editor.view.dom);
  });

  it("a destroyed editor closes the picker without throwing or taking focus", async () => {
    const { shell, editor } = mount();
    await openFromKeyboard(shell);
    const focus = vi.spyOn(editor.view, "focus");
    expect(() => editor.destroy()).not.toThrow();
    expect(overlay()).toBeNull();
    expect(focus).not.toHaveBeenCalled();
  });
});
