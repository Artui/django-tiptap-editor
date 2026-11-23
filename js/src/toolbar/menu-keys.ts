// Keyboard for a role=menu panel (WAI-ARIA APG Menu Button): a roving tabindex, so
// the focused item is the panel's only tabbable and the dropdown's Tab bridge
// treats it as both first and last; Up/Down wrap, Home/End, and a printable key
// moves to the next item whose label starts with it. Enter and Space are left to
// the native button click; Left/Right and Tab pass through untouched.
const MENU_ITEM = "[role=menuitem], [role=menuitemradio], [role=menuitemcheckbox]";

// A checked radio opens the menu; a checked checkbox is an action like the rest.
export function isCheckedRadio(item: HTMLElement): boolean {
  return item.matches("[role=menuitemradio][aria-checked=true]");
}

export function itemsOf(menu: HTMLElement): HTMLElement[] {
  return Array.from(menu.children).filter(
    (node): node is HTMLElement => node instanceof HTMLElement && node.matches(MENU_ITEM),
  );
}

function rove(menu: HTMLElement, to: HTMLElement): void {
  for (const item of itemsOf(menu)) {
    item.tabIndex = item === to ? 0 : -1;
  }
}

export function focusItem(menu: HTMLElement, to: HTMLElement): void {
  rove(menu, to);
  to.focus();
}

export function menuKeys(menu: HTMLElement): void {
  const items = itemsOf(menu);
  const start = items.find(isCheckedRadio) ?? items[0];
  if (start) {
    rove(menu, start);
  }
  menu.addEventListener("focusin", (event) => {
    if (event.target instanceof HTMLElement && items.includes(event.target)) {
      rove(menu, event.target);
    }
  });
  menu.addEventListener("keydown", (event) => {
    const at = items.indexOf(event.target as HTMLElement);
    if (at < 0 || event.ctrlKey || event.metaKey || event.altKey) {
      return;
    }
    let next: HTMLElement | undefined;
    if (event.key === "ArrowDown") {
      next = items[(at + 1) % items.length];
    } else if (event.key === "ArrowUp") {
      next = items[(at - 1 + items.length) % items.length];
    } else if (event.key === "Home") {
      next = items[0];
    } else if (event.key === "End") {
      next = items[items.length - 1];
    } else if (event.key.length === 1) {
      const char = event.key.toLowerCase();
      const order = [...items.slice(at + 1), ...items.slice(0, at + 1)];
      next = order.find((item) => item.textContent?.trim().toLowerCase().startsWith(char));
      if (!next) {
        return;
      }
    } else {
      return;
    }
    event.preventDefault();
    focusItem(menu, next);
  });
}
