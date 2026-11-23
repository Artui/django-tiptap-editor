// jsdom has no modal dialog API: this stands in for it, throwing where a browser does.
export function installDialog(): void {
  HTMLDialogElement.prototype.showModal = function (this: HTMLDialogElement): void {
    if (!this.isConnected || this.hasAttribute("open")) {
      throw new DOMException("showModal", "InvalidStateError");
    }
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function (this: HTMLDialogElement): void {
    this.removeAttribute("open");
  };
}

export function removeDialog(): void {
  delete (HTMLDialogElement.prototype as Partial<HTMLDialogElement>).showModal;
  delete (HTMLDialogElement.prototype as Partial<HTMLDialogElement>).close;
}
