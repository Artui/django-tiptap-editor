// jsdom has no popover API: this stands in for it, throwing where a browser does.
const shown = new WeakSet<HTMLElement>();

export function installPopover(): void {
  HTMLElement.prototype.showPopover = function (this: HTMLElement): void {
    if (!this.isConnected || shown.has(this) || this.getAttribute("popover") === null) {
      throw new DOMException("showPopover", "InvalidStateError");
    }
    shown.add(this);
  };
  HTMLElement.prototype.hidePopover = function (this: HTMLElement): void {
    if (this.getAttribute("popover") === null) {
      throw new DOMException("hidePopover", "InvalidStateError");
    }
    shown.delete(this);
  };
}

export function removePopover(): void {
  delete (HTMLElement.prototype as Partial<HTMLElement>).showPopover;
  delete (HTMLElement.prototype as Partial<HTMLElement>).hidePopover;
}

export function isShown(el: HTMLElement): boolean {
  return shown.has(el);
}
