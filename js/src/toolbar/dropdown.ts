// Toolbar dropdown: a trigger button plus a panel. The open panel stays in the
// dropdown, right after the trigger, and is shown as a manual popover: the top
// layer escapes the shell's overflow: hidden while the panel stays a DOM
// descendant of any modal or focus trap around the editor. Without the popover
// API it is portaled into the nearest dialog container, else the trigger's root
// node. Either way it is placed in the viewport beside the trigger. Closes on
// outside-click, Escape, the panel signalling done, or the editor's destruction.
// One panel is open at a time.
import type { Editor } from "../tiptap-runtime";
import { forwardTheme } from "./forward-theme";
import { applyLabel } from "./label";
import { placePanel } from "./place-panel";

export interface Dropdown {
  el: HTMLElement;
  trigger: HTMLButtonElement;
  panel: HTMLElement;
  close: () => void;
}

export interface DropdownOptions {
  title: string;
  triggerHTML: string;
  label?: string;
  editor?: Editor;
  buildPanel: (close: () => void) => HTMLElement;
}

// Marks a panel, so the DOM observer can skip a portaled one like a shell.
export const PANEL_ATTR = "data-tiptap-panel";

const openPanels = new Set<() => void>();

// The shell's focusout handler and its open panel: a portaled panel can be
// outside the shell, and focus moving between the two must count as staying inside.
const leaveHandlers = new WeakMap<HTMLElement, (event: FocusEvent) => void>();
const shellPanels = new WeakMap<HTMLElement, HTMLElement>();

export function registerShell(shell: HTMLElement, onLeave: (event: FocusEvent) => void): void {
  leaveHandlers.set(shell, onLeave);
}

export function openPanelIn(shell: HTMLElement): HTMLElement | null {
  return shellPanels.get(shell) ?? null;
}

function shellOf(node: Element): HTMLElement | null {
  for (let at = node.parentElement; at; at = at.parentElement) {
    if (leaveHandlers.has(at)) {
      return at;
    }
  }
  return null;
}

const TABBABLE =
  "a[href], button, input:not([type=hidden]), select, textarea, [tabindex], [contenteditable='true']";

function tabbables(root: ParentNode): HTMLElement[] {
  return Array.from(root.querySelectorAll<HTMLElement>(TABBABLE)).filter(
    (node) =>
      node.tabIndex >= 0 &&
      !node.matches(":disabled") &&
      !node.closest("[hidden]") &&
      getComputedStyle(node).display !== "none" &&
      (node.checkVisibility?.() ?? true),
  );
}

const DIALOG = "dialog[open], [role=dialog], [aria-modal=true], .modal";

function portalTarget(trigger: HTMLElement): ParentNode {
  const dialog = trigger.closest(DIALOG);
  if (dialog) {
    return dialog;
  }
  const root = trigger.getRootNode();
  return root instanceof ShadowRoot ? root : document.body;
}

function activeElementOf(node: Node): Element | null {
  const root = node.getRootNode();
  return root instanceof Document || root instanceof ShadowRoot ? root.activeElement : null;
}

export function createDropdown(opts: DropdownOptions): Dropdown {
  const el = document.createElement("div");
  el.className = "django-tiptap__dropdown";

  const trigger = document.createElement("button");
  trigger.type = "button";
  trigger.className = "django-tiptap__btn django-tiptap__dropdown-trigger";
  trigger.title = opts.title;
  trigger.setAttribute("aria-label", opts.title);
  trigger.setAttribute("aria-haspopup", "true");
  trigger.setAttribute("aria-expanded", "false");
  trigger.innerHTML = opts.triggerHTML;
  if (opts.label) {
    applyLabel(trigger, opts.label);
  }

  const panel = document.createElement("div");
  panel.className = "django-tiptap__panel";
  panel.setAttribute(PANEL_ATTR, "");

  let isOpen = false;
  let popped = false;
  let leaveFrom: ((event: FocusEvent) => void) | null = null;
  let shell: HTMLElement | null = null;
  let frame = 0;

  function close(): void {
    if (!isOpen) {
      return;
    }
    isOpen = false;
    const active = activeElementOf(panel);
    if (active && panel.contains(active)) {
      trigger.focus();
    }
    if (frame) {
      cancelAnimationFrame(frame);
      frame = 0;
    }
    if (popped) {
      popped = false;
      panel.hidePopover();
    }
    panel.remove();
    trigger.classList.remove("is-open");
    trigger.setAttribute("aria-expanded", "false");
    openPanels.delete(close);
    document.removeEventListener("mousedown", onOutside, true);
    document.removeEventListener("keydown", onKey, true);
    document.removeEventListener("scroll", schedule, true);
    window.removeEventListener("resize", schedule);
    opts.editor?.off("destroy", close);
    if (leaveFrom) {
      panel.removeEventListener("focusout", leaveFrom);
      leaveFrom = null;
    }
    if (shell) {
      if (shellPanels.get(shell) === panel) {
        shellPanels.delete(shell);
      }
      shell = null;
    }
  }

  function onOutside(event: MouseEvent): void {
    const path = event.composedPath();
    if (!path.includes(el) && !path.includes(panel)) {
      close();
    }
  }

  function onKey(event: KeyboardEvent): void {
    if (event.key === "Escape") {
      close();
    }
  }

  // Viewport coordinates from placePanel, converted to the panel's containing
  // block by measuring where left/top 0 lands (a positioned body, a translated
  // shadow host).
  function place(): void {
    frame = 0;
    if (!trigger.isConnected) {
      close();
      return;
    }
    const rect = trigger.getBoundingClientRect();
    const width = document.documentElement.clientWidth || window.innerWidth;
    const height = document.documentElement.clientHeight || window.innerHeight;
    if (rect.bottom < 0 || rect.top > height || rect.right < 0 || rect.left > width) {
      close();
      return;
    }
    panel.style.left = "0px";
    panel.style.top = "0px";
    panel.style.maxHeight = "";
    const origin = panel.getBoundingClientRect();
    const at = placePanel(rect, origin, { width, height });
    panel.style.left = `${at.left - origin.left}px`;
    panel.style.top = `${at.top - origin.top}px`;
    panel.style.maxHeight = `${at.maxHeight}px`;
  }

  function schedule(event: Event): void {
    if (event.target instanceof Node && panel.contains(event.target)) {
      return;
    }
    if (!frame) {
      frame = requestAnimationFrame(place);
    }
  }

  function open(): void {
    for (const closeOther of Array.from(openPanels)) {
      closeOther();
    }
    panel.replaceChildren(opts.buildPanel(close));
    shell = shellOf(el);
    if (typeof panel.showPopover === "function") {
      panel.setAttribute("popover", "manual");
      el.appendChild(panel);
      panel.showPopover();
      popped = true;
    } else {
      panel.removeAttribute("popover");
      forwardTheme(shell ?? el, panel);
      portalTarget(trigger).appendChild(panel);
    }
    isOpen = true;
    if (shell) {
      shellPanels.set(shell, panel);
      const onLeave = leaveHandlers.get(shell);
      if (onLeave && !shell.contains(panel)) {
        leaveFrom = onLeave;
        panel.addEventListener("focusout", onLeave);
      }
    }
    trigger.classList.add("is-open");
    trigger.setAttribute("aria-expanded", "true");
    openPanels.add(close);
    document.addEventListener("mousedown", onOutside, true);
    document.addEventListener("keydown", onKey, true);
    document.addEventListener("scroll", schedule, true);
    window.addEventListener("resize", schedule);
    opts.editor?.on("destroy", close);
    place();
  }

  // A portaled panel is not after the trigger in DOM order, so Tab is bridged by
  // hand into it and back out to the control after the trigger.
  trigger.addEventListener("keydown", (event) => {
    if (!isOpen || event.key !== "Tab" || event.shiftKey) {
      return;
    }
    const first = tabbables(panel)[0];
    if (first) {
      event.preventDefault();
      first.focus();
    }
  });
  panel.addEventListener("keydown", (event) => {
    if (event.key !== "Tab") {
      return;
    }
    const inside = tabbables(panel);
    if (event.shiftKey && event.target === inside[0]) {
      event.preventDefault();
      trigger.focus();
    } else if (!event.shiftKey && event.target === inside[inside.length - 1]) {
      event.preventDefault();
      const order = tabbables(trigger.getRootNode() as ParentNode).filter((n) => !panel.contains(n));
      const at = order.indexOf(trigger);
      const next = (at < 0 ? undefined : order[at + 1]) ?? trigger;
      close();
      next.focus();
    }
  });

  trigger.addEventListener("mousedown", (event) => event.preventDefault());
  trigger.addEventListener("click", (event) => {
    event.preventDefault();
    if (isOpen) {
      close();
    } else {
      open();
    }
  });

  el.appendChild(trigger);
  return { el, trigger, panel, close };
}
