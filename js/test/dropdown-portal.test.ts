import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DjangoTipTap from "../src/index";
import type { TipTapConfig } from "../src/default-config";
import type { Editor } from "../src/tiptap-runtime";
import { installPopover, isShown, removePopover } from "./popover-stub";

const TOOLBAR = [["bold"], ["fontSize", "highlight"]];

interface Mounted {
  id: string;
  editor: Editor;
  shell: HTMLElement;
  root: Document | ShadowRoot;
  form: HTMLFormElement;
  outside: HTMLInputElement;
  events: string[];
}

let seq = 0;
const mounted: string[] = [];

function mount(config: TipTapConfig = {}, shadow = false): Mounted {
  const form = document.createElement("form");
  const textarea = document.createElement("textarea");
  textarea.id = `portal-${++seq}`;
  textarea.value = "<p>hello</p>";
  const outside = document.createElement("input");
  let root: Document | ShadowRoot = document;
  if (shadow) {
    const host = document.createElement("div");
    document.body.appendChild(host);
    root = host.attachShadow({ mode: "open" });
    root.append(form);
  } else {
    document.body.appendChild(form);
  }
  form.append(textarea, outside);
  const events: string[] = [];
  textarea.addEventListener("change", () => events.push("change"));
  const editor = DjangoTipTap.init(textarea, { toolbar: TOOLBAR, ...config });
  mounted.push(textarea.id);
  const shell = textarea.nextElementSibling as HTMLElement;
  return { id: textarea.id, editor, shell, root, form, outside, events };
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

function openPanel(root: Document | ShadowRoot): HTMLElement | undefined {
  return Array.from(root.querySelectorAll<HTMLElement>(".django-tiptap__panel")).find(
    (panel) => !panel.hidden,
  );
}

function items(panel: HTMLElement): HTMLButtonElement[] {
  return Array.from(panel.querySelectorAll<HTMLButtonElement>("button"));
}

// Composed, as a real keypress is: a non-composed event stops at a shadow root.
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

const tick = (): Promise<void> => new Promise((resolve) => setTimeout(resolve, 0));
const frame = (): Promise<void> => new Promise((resolve) => requestAnimationFrame(() => resolve()));

afterEach(() => {
  for (const id of mounted.splice(0)) {
    DjangoTipTap.destroy(id);
  }
  document.body.innerHTML = "";
  document.head.querySelectorAll("style[data-test]").forEach((style) => style.remove());
  vi.restoreAllMocks();
  removePopover();
});

describe("the open panel stays in its dropdown as a popover", () => {
  beforeEach(installPopover);

  it("is shown right after the trigger, and hidden and removed on close", () => {
    const { shell } = mount();
    const button = trigger(shell, "Font size");
    button.click();
    const panel = openPanel(document)!;
    expect(panel.parentElement?.classList.contains("django-tiptap__dropdown")).toBe(true);
    expect(panel.previousElementSibling).toBe(button);
    expect(panel.getAttribute("popover")).toBe("manual");
    expect(isShown(panel)).toBe(true);
    key(document.body, "Escape");
    expect(isShown(panel)).toBe(false);
    expect(panel.isConnected).toBe(false);
  });

  it("stays in its dropdown inside a shadow root", () => {
    const { shell, root } = mount({}, true);
    const button = trigger(shell, "Font size");
    button.click();
    expect(openPanel(root)?.parentElement).toBe(button.parentElement);
  });

  it("reopens after a close", () => {
    const { shell } = mount();
    const button = trigger(shell, "Font size");
    button.click();
    button.click();
    button.click();
    expect(isShown(openPanel(document)!)).toBe(true);
  });

  it("inherits the shell's tokens instead of taking an inline copy", () => {
    const style = document.createElement("style");
    style.dataset.test = "";
    style.textContent = ".django-tiptap { --tiptap-bg: rgb(1, 2, 3); }";
    document.head.appendChild(style);
    const { shell } = mount();
    trigger(shell, "Font size").click();
    expect(openPanel(document)?.getAttribute("style") ?? "").not.toContain("--tiptap-bg");
  });
});

describe("without the popover API the open panel is portaled to the trigger's root node", () => {
  it("appends to document.body on open and removes it on close", () => {
    const { shell } = mount();
    trigger(shell, "Font size").click();
    const panel = openPanel(document);
    expect(panel?.parentNode).toBe(document.body);
    key(document.body, "Escape");
    expect(panel?.isConnected).toBe(false);
  });

  it("appends to the shadow root when the editor is inside one", () => {
    const { shell, root } = mount({}, true);
    trigger(shell, "Font size").click();
    expect(openPanel(root)?.parentNode).toBe(root);
  });

  it("forwards the shell's tokens onto the panel inline", () => {
    const style = document.createElement("style");
    style.dataset.test = "";
    style.textContent = ".django-tiptap { --tiptap-bg: rgb(1, 2, 3); }";
    document.head.appendChild(style);
    const { shell } = mount();
    trigger(shell, "Font size").click();
    expect(openPanel(document)?.style.getPropertyValue("--tiptap-bg")).toBe("rgb(1, 2, 3)");
  });
});

describe.each(["popover", "portal"])("with the %s path", (path) => {
  beforeEach(() => {
    if (path === "popover") {
      installPopover();
    }
  });

  describe("outside click", () => {
    it("keeps the panel open for a composed mousedown on an item in a shadow root", () => {
      const { shell, root } = mount({}, true);
      const button = trigger(shell, "Font size");
      button.click();
      const item = items(openPanel(root)!)[1];
      item.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, composed: true }));
      expect(button.getAttribute("aria-expanded")).toBe("true");
    });

    it("keeps the panel open for a mousedown on an item in the document", () => {
      const { shell } = mount();
      const button = trigger(shell, "Font size");
      button.click();
      items(openPanel(document)!)[1].dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
      expect(button.getAttribute("aria-expanded")).toBe("true");
    });

    it("closes on a mousedown and click on the open trigger", () => {
      const { shell } = mount();
      const button = trigger(shell, "Font size");
      button.click();
      button.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, composed: true }));
      button.click();
      expect(button.getAttribute("aria-expanded")).toBe("false");
      expect(openPanel(document)).toBeUndefined();
    });

    it("closes on a mousedown elsewhere", () => {
      const { shell } = mount();
      const button = trigger(shell, "Font size");
      button.click();
      document.body.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
      expect(button.getAttribute("aria-expanded")).toBe("false");
    });
  });

  describe("focus and tab order", () => {
    it("Tab on the open trigger focuses the panel's first item", () => {
      const { shell } = mount();
      const button = trigger(shell, "Font size");
      button.click();
      button.focus();
      const event = key(button, "Tab");
      expect(document.activeElement).toBe(items(openPanel(document)!)[0]);
      expect(event.defaultPrevented).toBe(true);
    });

    it("Tab on the last item closes and focuses the control after the trigger", () => {
      const { shell } = mount();
      const button = trigger(shell, "Font size");
      button.click();
      const list = items(openPanel(document)!);
      list[list.length - 1].focus();
      const event = key(list[list.length - 1], "Tab");
      expect(button.getAttribute("aria-expanded")).toBe("false");
      expect(document.activeElement).toBe(trigger(shell, "Highlight"));
      expect(event.defaultPrevented).toBe(true);
    });

    it("Shift+Tab on the first item focuses the trigger and leaves the panel open", () => {
      const { shell } = mount();
      const button = trigger(shell, "Font size");
      button.click();
      const first = items(openPanel(document)!)[0];
      first.focus();
      const event = key(first, "Tab", true);
      expect(document.activeElement).toBe(button);
      expect(button.getAttribute("aria-expanded")).toBe("true");
      expect(event.defaultPrevented).toBe(true);
    });

    it("Escape with focus in the panel returns focus to the trigger", () => {
      const { shell } = mount();
      const button = trigger(shell, "Font size");
      button.click();
      const panel = openPanel(document)!;
      items(panel)[1].focus();
      key(items(panel)[1], "Escape");
      expect(document.activeElement).toBe(button);
      expect(panel.isConnected).toBe(false);
    });

    it("Escape in a shadow root returns focus to the trigger there", () => {
      const { shell, root } = mount({}, true);
      const button = trigger(shell, "Font size");
      button.click();
      const panel = openPanel(root)!;
      items(panel)[1].focus();
      key(items(panel)[1], "Escape");
      expect(root.activeElement).toBe(button);
      expect(panel.isConnected).toBe(false);
    });

    it("Tab on a closed trigger is left to the browser", () => {
      const { shell } = mount();
      const button = trigger(shell, "Font size");
      button.click();
      button.click();
      button.focus();
      const event = key(button, "Tab");
      expect(event.defaultPrevented).toBe(false);
      expect(document.activeElement).toBe(button);
    });

    it("Shift+Tab on the open trigger is left to the browser", () => {
      const { shell } = mount();
      const button = trigger(shell, "Font size");
      button.click();
      button.focus();
      const event = key(button, "Tab", true);
      expect(event.defaultPrevented).toBe(false);
      expect(document.activeElement).toBe(button);
    });

    it("Shift+Tab on a later item is left to the browser and keeps the panel open", () => {
      const { shell } = mount();
      const button = trigger(shell, "Font size");
      button.click();
      const second = items(openPanel(document)!)[1];
      second.focus();
      const event = key(second, "Tab", true);
      expect(event.defaultPrevented).toBe(false);
      expect(button.getAttribute("aria-expanded")).toBe("true");
      expect(document.activeElement).toBe(second);
    });

    it("Tab on a non-last item is left to the browser and keeps the panel open", () => {
      const { shell } = mount();
      const button = trigger(shell, "Font size");
      button.click();
      const first = items(openPanel(document)!)[0];
      first.focus();
      const event = key(first, "Tab");
      expect(event.defaultPrevented).toBe(false);
      expect(button.getAttribute("aria-expanded")).toBe("true");
      expect(document.activeElement).toBe(first);
    });

    it("Tab on the last item with nothing after the trigger lands back on the trigger", () => {
      const { shell, outside } = mount({ toolbar: [["fontSize"]] });
      outside.remove();
      shell.querySelectorAll<HTMLElement>("[contenteditable]").forEach((node) => {
        node.setAttribute("tabindex", "-1");
      });
      const button = trigger(shell, "Font size");
      button.click();
      const list = items(openPanel(document)!);
      const refocused = vi.spyOn(list[0], "focus");
      list[list.length - 1].focus();
      key(list[list.length - 1], "Tab");
      expect(button.getAttribute("aria-expanded")).toBe("false");
      expect(refocused).not.toHaveBeenCalled();
      expect(document.activeElement).toBe(button);
    });
  });

  describe("the textarea's change event", () => {
    it("does not fire moving into the colour panel, and fires once leaving it", async () => {
      const { editor, shell, outside, events } = mount({
        toolbar: [["bold", "color"]],
        colorPicker: true,
      } as TipTapConfig);
      editor.commands.focus();
      editor.chain().setTextSelection({ from: 1, to: 6 }).toggleBold().run();
      trigger(shell, "Text color").click();
      const picker = document.querySelector<HTMLInputElement>(".django-tiptap__picker-input")!;
      picker.focus();
      await tick();
      expect(events).toEqual([]);
      outside.focus();
      await tick();
      expect(events).toEqual(["change"]);
    });
  });

  describe("teardown", () => {
    it("destroy() with a panel open removes the panel and its listeners", () => {
      const { id, shell } = mount();
      trigger(shell, "Font size").click();
      const panel = openPanel(document)!;
      const fromDocument = vi.spyOn(document, "removeEventListener");
      const fromWindow = vi.spyOn(window, "removeEventListener");
      DjangoTipTap.destroy(id);
      const removed = [...fromDocument.mock.calls, ...fromWindow.mock.calls].map((call) => call[0]);
      expect(removed).toEqual(expect.arrayContaining(["mousedown", "keydown", "scroll", "resize"]));
      expect(panel.isConnected).toBe(false);
    });

    it("a destructive swap with a panel open removes the panel", async () => {
      const { form, shell } = mount();
      trigger(shell, "Font size").click();
      const panel = openPanel(document)!;
      form.remove();
      await tick();
      expect(panel.isConnected).toBe(false);
    });

    it("the DOM observer does not scan the open panel", async () => {
      const { shell } = mount();
      const scanned: Element[] = [];
      const original = Element.prototype.querySelectorAll;
      vi.spyOn(Element.prototype, "querySelectorAll").mockImplementation(function (
        this: Element,
        selector: string,
      ) {
        scanned.push(this);
        return original.call(this, selector);
      });
      trigger(shell, "Font size").click();
      const panel = openPanel(document)!;
      await tick();
      expect(scanned.filter((el) => el === panel || panel.contains(el))).toEqual([]);
    });
  });

  describe("placement", () => {
    function stubRects(triggerRect: () => DOMRect): void {
      vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(function (
        this: HTMLElement,
      ) {
        if (this.classList.contains("django-tiptap__panel")) {
          const left = parseFloat(this.style.left) || 0;
          const top = parseFloat(this.style.top) || 0;
          return { left, top, right: left + 150, bottom: top + 100, width: 150, height: 100 } as DOMRect;
        }
        if (this.classList.contains("django-tiptap__dropdown-trigger")) {
          return triggerRect();
        }
        return { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 } as DOMRect;
      });
    }

    function rect(left: number, top: number): DOMRect {
      return { left, top, right: left + 30, bottom: top + 30, width: 30, height: 30 } as DOMRect;
    }

    it("keeps the panel inside the viewport for a trigger at the right edge", () => {
      stubRects(() => rect(window.innerWidth - 30, 10));
      const { shell } = mount();
      trigger(shell, "Font size").click();
      const panel = openPanel(document)!;
      expect(parseFloat(panel.style.left) + 150).toBeLessThanOrEqual(window.innerWidth);
    });

    it("follows the trigger on resize and scroll, and closes once it leaves the viewport", async () => {
      let at = rect(100, 10);
      stubRects(() => at);
      const { shell } = mount();
      const button = trigger(shell, "Font size");
      button.click();
      const panel = openPanel(document)!;
      expect(panel.style.left).toBe("100px");
      at = rect(200, 10);
      window.dispatchEvent(new Event("resize"));
      await frame();
      expect(panel.style.left).toBe("200px");
      at = rect(300, 50);
      document.dispatchEvent(new Event("scroll"));
      await frame();
      expect([panel.style.left, panel.style.top]).toEqual(["300px", "84px"]);
      at = rect(300, -100);
      document.dispatchEvent(new Event("scroll"));
      await frame();
      expect(button.getAttribute("aria-expanded")).toBe("false");
      expect(panel.isConnected).toBe(false);
    });
    it.each([
      ["below the viewport", () => rect(100, window.innerHeight + 10)],
      ["right of the viewport", () => rect(window.innerWidth + 10, 100)],
      ["left of the viewport", () => rect(-100, 100)],
    ])("closes once the trigger is %s", async (_name, next) => {
      let at = rect(100, 100);
      stubRects(() => at);
      const { shell } = mount();
      const button = trigger(shell, "Font size");
      button.click();
      const panel = openPanel(document)!;
      at = next();
      window.dispatchEvent(new Event("resize"));
      await frame();
      expect(button.getAttribute("aria-expanded")).toBe("false");
      expect(panel.isConnected).toBe(false);
    });

    it("closes once the trigger is no longer connected", async () => {
      stubRects(() => rect(100, 100));
      const { shell } = mount();
      const button = trigger(shell, "Font size");
      button.click();
      const panel = openPanel(document)!;
      button.remove();
      window.dispatchEvent(new Event("resize"));
      await frame();
      expect(panel.isConnected).toBe(false);
    });

    it("ignores a scroll inside the panel but follows one elsewhere", async () => {
      let at = rect(100, 10);
      stubRects(() => at);
      const { shell } = mount();
      trigger(shell, "Font size").click();
      const panel = openPanel(document)!;
      at = rect(200, 10);
      items(panel)[1].dispatchEvent(new Event("scroll"));
      await frame();
      expect(panel.style.left).toBe("100px");
      document.dispatchEvent(new Event("scroll"));
      await frame();
      expect(panel.style.left).toBe("200px");
    });
  });
});

describe("the DOM observer and a portaled panel", () => {
  it("does not mount a field added inside the open panel", async () => {
    const { shell } = mount();
    trigger(shell, "Font size").click();
    const panel = openPanel(document)!;
    const field = document.createElement("textarea");
    field.setAttribute("data-tiptap-config", "{}");
    panel.appendChild(field);
    await tick();
    expect(field.nextElementSibling).toBeNull();
    expect(field.hasAttribute("data-tiptap-bound")).toBe(false);
  });

  it("does not look for editors inside a panel that was removed", async () => {
    const { shell } = mount();
    const button = trigger(shell, "Font size");
    button.click();
    const panel = openPanel(document)!;
    await tick();
    const contains = vi.spyOn(panel, "contains");
    button.click();
    contains.mockClear();
    await tick();
    expect(panel.isConnected).toBe(false);
    expect(contains).not.toHaveBeenCalled();
  });
});
