// Image upload + safe insertion. Uploads go to config.imageUploadUrl as
// multipart/form-data (field "file") and expect {"location": "<url>"} back
// (the TinyMCE-ecosystem convention). The returned URL — and any picker value —
// is inserted as a src only after protocol validation.
import { configFor } from "./editor-config";
import type { Editor } from "./tiptap-runtime";

const ALLOWED_IMAGE_SCHEMES = ["http:", "https:", "data:"];

export function isAllowedImageSrc(src: string): boolean {
  try {
    return ALLOWED_IMAGE_SCHEMES.includes(new URL(src, window.location.href).protocol);
  } catch {
    return false;
  }
}

export function insertImage(editor: Editor, src: string): void {
  if (!isAllowedImageSrc(src)) {
    console.error(`[DjangoTipTap] refusing image with disallowed src: ${src}`);
    return;
  }
  editor.chain().focus().setImage({ src }).run();
}

function csrfToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export async function uploadImage(url: string, file: File): Promise<string> {
  const body = new FormData();
  body.append("file", file);
  const token = csrfToken();
  const res = await fetch(url, {
    method: "POST",
    body,
    headers: token ? { "X-CSRFToken": token } : {},
  });
  if (!res.ok) {
    let message = res.statusText;
    try {
      const data = await res.json();
      if (data && typeof data.error === "string") {
        message = data.error;
      }
    } catch {
      // non-JSON error body; keep statusText
    }
    throw new Error(message);
  }
  const data = await res.json();
  return data.location as string;
}

export async function uploadAndInsert(editor: Editor, file: File): Promise<void> {
  const url = configFor(editor).imageUploadUrl;
  if (!url) {
    return;
  }
  try {
    insertImage(editor, await uploadImage(url, file));
  } catch (err) {
    console.error("[DjangoTipTap] image upload failed", err);
  }
}

// Toolbar "Upload…" action: open a native file picker, then upload.
export function uploadViaFileDialog(editor: Editor): void {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = configFor(editor).imageFileTypes
    ? configFor(editor)
        .imageFileTypes!.split(",")
        .map((ext) => `.${ext.trim()}`)
        .join(",")
    : "image/*";
  input.addEventListener("change", () => {
    const file = input.files?.[0];
    if (file) {
      void uploadAndInsert(editor, file);
    }
  });
  input.click();
}

// Paste/drop of image files → upload (when imageUploadUrl is set). Pasted HTML
// (with <img>) has no files and falls through to the schema parser.
export function wireImageDropPaste(editor: Editor): void {
  const dom = editor.view.dom as HTMLElement;
  const onFiles = (files: FileList | undefined | null, event: Event): void => {
    if (!configFor(editor).imageUploadUrl || !files || files.length === 0) {
      return;
    }
    const images = Array.from(files).filter((f) => f.type.startsWith("image/"));
    if (images.length === 0) {
      return;
    }
    event.preventDefault();
    images.forEach((file) => void uploadAndInsert(editor, file));
  };
  dom.addEventListener("paste", (event) => onFiles((event as ClipboardEvent).clipboardData?.files, event));
  dom.addEventListener("drop", (event) => onFiles((event as DragEvent).dataTransfer?.files, event));
}
