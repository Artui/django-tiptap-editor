// Library picker: a modal that GETs config.imageListUrl (-> [{title, value}])
// and inserts the chosen image (protocol-validated via insertImage).
import { configFor } from "./editor-config";
import { translatorFor } from "./i18n";
import type { Editor } from "./tiptap-runtime";
import { insertImage } from "./upload";

interface ImageItem {
  title: string;
  value: string;
}

export async function openImagePicker(editor: Editor): Promise<void> {
  const url = configFor(editor).imageListUrl;
  if (!url) {
    return;
  }
  const t = translatorFor(editor);

  const overlay = document.createElement("div");
  overlay.className = "django-tiptap__modal-overlay";
  const modal = document.createElement("div");
  modal.className = "django-tiptap__modal";
  overlay.appendChild(modal);

  const header = document.createElement("div");
  header.className = "django-tiptap__modal-header";
  const heading = document.createElement("span");
  heading.textContent = t("pickerTitle");
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

  function close(): void {
    overlay.remove();
    document.removeEventListener("keydown", onKey, true);
    editor.off("destroy", close);
  }
  function onKey(event: KeyboardEvent): void {
    if (event.key === "Escape") {
      close();
    }
  }
  overlay.addEventListener("mousedown", (event) => {
    if (event.target === overlay) {
      close();
    }
  });
  closeBtn.addEventListener("click", close);
  document.addEventListener("keydown", onKey, true);
  // The overlay is portaled to <body> and the keydown listener lives on
  // `document` — neither sits inside the editor shell, so removing the shell does
  // not clean them up. Dispose them if the editor is torn down while the picker
  // is open (e.g. a destructive DOM swap removes the editor mid-pick).
  editor.on("destroy", close);
  document.body.appendChild(overlay);

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
  } catch {
    bodyEl.textContent = t("pickerError");
  }
}
