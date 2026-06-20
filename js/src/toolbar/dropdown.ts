// Minimal toolbar dropdown: a trigger button plus a panel that opens below it.
// Closes on outside-click, Escape, or when the panel signals done. One panel is
// open at a time (opening one closes others via a shared registry).
export interface Dropdown {
  el: HTMLElement;
  trigger: HTMLButtonElement;
  panel: HTMLElement;
  close: () => void;
}

const openPanels = new Set<() => void>();

export interface DropdownOptions {
  title: string;
  triggerHTML: string;
  buildPanel: (close: () => void) => HTMLElement;
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
  trigger.innerHTML = opts.triggerHTML;

  const panel = document.createElement("div");
  panel.className = "django-tiptap__panel";
  panel.hidden = true;

  function close(): void {
    if (panel.hidden) {
      return;
    }
    panel.hidden = true;
    trigger.classList.remove("is-open");
    openPanels.delete(close);
    document.removeEventListener("mousedown", onOutside, true);
    document.removeEventListener("keydown", onKey, true);
  }

  function onOutside(event: MouseEvent): void {
    if (!el.contains(event.target as globalThis.Node)) {
      close();
    }
  }

  function onKey(event: KeyboardEvent): void {
    if (event.key === "Escape") {
      close();
    }
  }

  function open(): void {
    for (const closeOther of Array.from(openPanels)) {
      closeOther();
    }
    panel.innerHTML = "";
    panel.appendChild(opts.buildPanel(close));
    panel.hidden = false;
    trigger.classList.add("is-open");
    openPanels.add(close);
    document.addEventListener("mousedown", onOutside, true);
    document.addEventListener("keydown", onKey, true);
  }

  trigger.addEventListener("mousedown", (event) => event.preventDefault());
  trigger.addEventListener("click", (event) => {
    event.preventDefault();
    if (panel.hidden) {
      open();
    } else {
      close();
    }
  });

  el.appendChild(trigger);
  el.appendChild(panel);
  return { el, trigger, panel, close };
}
