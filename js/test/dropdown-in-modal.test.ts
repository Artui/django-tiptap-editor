import { afterEach, describe, expect, it } from "vitest";

import DjangoTipTap from "../src/index";
import { installPopover, removePopover } from "./popover-stub";

const FOCUSABLE = [
  "a",
  "button",
  "input",
  "textarea",
  "select",
  "details",
  "[tabindex]",
  '[contenteditable="true"]',
]
  .map((selector) => `${selector}:not([tabindex^="-"])`)
  .join(",");

// Bootstrap's focusableChildren: not disabled and visible.
function firstFocusable(trap: HTMLElement): HTMLElement | undefined {
  return Array.from(trap.querySelectorAll<HTMLElement>(FOCUSABLE)).find(
    (node) =>
      !node.matches(":disabled") &&
      !node.closest("[hidden]") &&
      getComputedStyle(node).display !== "none",
  );
}

let seq = 0;
const mounted: string[] = [];
const traps: Array<() => void> = [];

function container(kind: "modal" | "dialog"): HTMLElement {
  if (kind === "dialog") {
    const dialog = document.createElement("dialog");
    dialog.setAttribute("open", "");
    return dialog;
  }
  const modal = document.createElement("div");
  modal.className = "modal";
  modal.setAttribute("role", "dialog");
  modal.setAttribute("aria-modal", "true");
  const inner = document.createElement("div");
  inner.className = "modal-body";
  modal.appendChild(inner);
  return modal;
}

function mountIn(host: HTMLElement): HTMLElement {
  const textarea = document.createElement("textarea");
  textarea.id = `modal-${++seq}`;
  textarea.value = "<p>hello</p>";
  (host.querySelector(".modal-body") ?? host).appendChild(textarea);
  document.body.appendChild(host);
  DjangoTipTap.init(textarea, { toolbar: [["bold", "fontSize"]] });
  mounted.push(textarea.id);
  return textarea.nextElementSibling as HTMLElement;
}

// Shaped like Bootstrap 5.3 focustrap.js _handleFocusin: focus leaving the trap goes to its first focusable.
function trapFocus(trap: HTMLElement): void {
  const onFocusin = (event: FocusEvent): void => {
    const target = event.target as Node;
    if (trap === target || trap.contains(target)) {
      return;
    }
    firstFocusable(trap)?.focus();
  };
  document.addEventListener("focusin", onFocusin);
  traps.push(() => document.removeEventListener("focusin", onFocusin));
}

function fontSize(shell: HTMLElement): HTMLButtonElement {
  return shell.querySelector<HTMLButtonElement>(
    '.django-tiptap__dropdown-trigger[aria-label^="Font size"]',
  )!;
}

function openPanel(): HTMLElement {
  return document.querySelector<HTMLElement>(".django-tiptap__panel")!;
}

function key(target: Element, name: string): void {
  target.dispatchEvent(
    new KeyboardEvent("keydown", { key: name, bubbles: true, cancelable: true, composed: true }),
  );
}

// Enter on a focused button: the keydown, then the click the browser synthesises.
function pressEnter(button: HTMLButtonElement): void {
  key(button, "Enter");
  button.click();
}

afterEach(() => {
  for (const id of mounted.splice(0)) {
    DjangoTipTap.destroy(id);
  }
  for (const release of traps.splice(0)) {
    release();
  }
  document.body.innerHTML = "";
  removePopover();
});

describe.each(["popover", "portal"])("inside a modal, on the %s path", (path) => {
  function setup(kind: "modal" | "dialog"): { host: HTMLElement; shell: HTMLElement } {
    if (path === "popover") {
      installPopover();
    }
    const host = container(kind);
    return { host, shell: mountIn(host) };
  }

  it.each(["modal", "dialog"] as const)("the open panel is a descendant of the %s", (kind) => {
    const { host, shell } = setup(kind);
    fontSize(shell).click();
    expect(host.contains(openPanel())).toBe(true);
  });

  it.each(["modal", "dialog"] as const)(
    "Enter then Tab in a focus-trapped %s lands on the panel's first item",
    (kind) => {
      const { host, shell } = setup(kind);
      trapFocus(host);
      const button = fontSize(shell);
      button.focus();
      pressEnter(button);
      key(button, "Tab");
      const first = openPanel().querySelector("button");
      expect(document.activeElement).toBe(first);
      expect(document.activeElement?.getAttribute("aria-label")).not.toBe("Bold");
    },
  );

  it("Escape in a focus-trapped modal returns focus to the trigger and removes the panel", () => {
    const { host, shell } = setup("modal");
    trapFocus(host);
    const button = fontSize(shell);
    button.focus();
    pressEnter(button);
    key(button, "Tab");
    const panel = openPanel();
    key(document.activeElement!, "Escape");
    expect(document.activeElement).toBe(button);
    expect(panel.isConnected).toBe(false);
  });
});

describe.each(["popover", "portal"])("Escape inside a modal, on the %s path", (path) => {
  it.each(["modal", "dialog"] as const)("closes the panel but not the %s", (kind) => {
    if (path === "popover") {
      installPopover();
    }
    const host = container(kind);
    const shell = mountIn(host);
    const seen: string[] = [];
    host.addEventListener("keydown", (event) => seen.push(event.key));
    const button = fontSize(shell);
    button.click();
    const item = openPanel().querySelector("button")!;
    item.focus();
    const event = new KeyboardEvent("keydown", {
      key: "Escape",
      bubbles: true,
      cancelable: true,
      composed: true,
    });
    item.dispatchEvent(event);
    expect(seen).toEqual([]);
    expect(event.defaultPrevented).toBe(true);
    expect(document.activeElement).toBe(button);
    expect(button.getAttribute("aria-expanded")).toBe("false");
  });

  it("closes the panel when its dialog closes", () => {
    if (path === "popover") {
      installPopover();
    }
    const host = container("dialog");
    const shell = mountIn(host);
    const button = fontSize(shell);
    button.click();
    const panel = openPanel();
    host.removeAttribute("open");
    host.dispatchEvent(new Event("close"));
    expect(panel.isConnected).toBe(false);
    expect(button.getAttribute("aria-expanded")).toBe("false");
  });
});

describe("the portal path picks the nearest dialog container by any one marker", () => {
  function single(marker: "role" | "aria" | "class"): HTMLElement {
    const box = document.createElement("div");
    if (marker === "role") {
      box.setAttribute("role", "dialog");
    } else if (marker === "aria") {
      box.setAttribute("aria-modal", "true");
    } else {
      box.className = "modal";
    }
    return box;
  }

  it.each(["role", "aria", "class"] as const)("portals into a container marked by %s", (marker) => {
    const box = single(marker);
    const shell = mountIn(box);
    fontSize(shell).click();
    expect(openPanel().parentElement).toBe(box);
  });
});

describe("the portal path outside any modal", () => {
  it("still portals to document.body", () => {
    const host = document.createElement("div");
    const shell = mountIn(host);
    fontSize(shell).click();
    expect(openPanel().parentNode).toBe(document.body);
  });
});
