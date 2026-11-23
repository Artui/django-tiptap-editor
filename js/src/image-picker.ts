// Library picker: a modal <dialog> that GETs config.imageListUrl (-> [{title, value}])
// and inserts the chosen image (protocol-validated via insertImage).
import { configFor } from "./editor-config";
import { translatorFor } from "./i18n";
import type { Editor } from "./tiptap-runtime";
import { insertImage } from "./upload";

interface ImageItem {
  title: string;
  value: string;
}

let seq = 0;

export async function openImagePicker(editor: Editor): Promise<void> {
  const url = configFor(editor).imageListUrl;
  if (!url) {
    return;
  }
  const t = translatorFor(editor);

  // The dialog fills the viewport and is the dimmed overlay; .django-tiptap__modal is the box.
  const dialog = document.createElement("dialog");
  dialog.className = "django-tiptap__modal-overlay";
  dialog.setAttribute("aria-modal", "true");
  const modal = document.createElement("div");
  modal.className = "django-tiptap__modal";
  dialog.appendChild(modal);

  const header = document.createElement("div");
  header.className = "django-tiptap__modal-header";
  const heading = document.createElement("span");
  heading.id = `django-tiptap-picker-${++seq}`;
  heading.textContent = t("pickerTitle");
  dialog.setAttribute("aria-labelledby", heading.id);
  const closeBtn = document.createElement("button");
  closeBtn.type = "button";
  closeBtn.className = "django-tiptap__modal-close";
  closeBtn.setAttribute("aria-label", t("close"));
  closeBtn.textContent = "×";
  header.appendChild(heading);
  header.appendChild(closeBtn);

  const bodyEl = document.createElement("div");
  bodyEl.className = "django-tiptap__modal-body";
  bodyEl.textContent = "…";

  modal.appendChild(header);
  modal.appendChild(bodyEl);

  // Each path runs this once: it removes what fired it, and destroy is unsubscribed.
  function finish(returnFocus: boolean): void {
    editor.off("destroy", onDestroy);
    dialog.close();
    dialog.remove();
    if (returnFocus) {
      editor.view.focus();
    }
  }
  function onDestroy(): void {
    finish(false);
  }
  const close = (): void => finish(true);

  dialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    close();
  });
  // Tab wraps inside the dialog rather than leaving it for the browser's own UI.
  dialog.addEventListener("keydown", (event) => {
    if (event.key !== "Tab") {
      return;
    }
    const stops = Array.from(dialog.querySelectorAll<HTMLElement>("button"));
    const first = stops[0];
    const last = stops[stops.length - 1];
    const active = document.activeElement;
    if (event.shiftKey ? active === first : active === last) {
      event.preventDefault();
      (event.shiftKey ? last : first).focus();
    }
  });
  // The press's default action would otherwise move focus off the editor again.
  dialog.addEventListener("mousedown", (event) => {
    if (event.target === dialog) {
      event.preventDefault();
      close();
    }
  });
  closeBtn.addEventListener("click", close);
  editor.on("destroy", onDestroy);
  document.body.appendChild(dialog);
  dialog.showModal();
  closeBtn.focus();

  try {
    const items: ImageItem[] = await (await fetch(url)).json();
    bodyEl.textContent = "";
    if (items.length === 0) {
      bodyEl.textContent = t("pickerEmpty");
      return;
    }
    const grid = document.createElement("div");
    grid.className = "django-tiptap__picker-grid";
    for (const item of items) {
      const tile = document.createElement("button");
      tile.type = "button";
      tile.className = "django-tiptap__picker-item";
      tile.title = item.title;
      const thumb = document.createElement("img");
      thumb.src = item.value;
      thumb.alt = item.title;
      const label = document.createElement("span");
      label.textContent = item.title;
      tile.appendChild(thumb);
      tile.appendChild(label);
      tile.addEventListener("click", () => {
        insertImage(editor, item.value);
        close();
      });
      grid.appendChild(tile);
    }
    bodyEl.appendChild(grid);
    // A no-op if the picker was closed meanwhile: a removed element takes no focus.
    (grid.firstElementChild as HTMLElement).focus();
  } catch {
    bodyEl.textContent = t("pickerError");
  }
}
