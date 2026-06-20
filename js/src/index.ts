// window.DjangoTipTap — the public glue entry. In place today: the build
// pipeline, the runtime seam, and a minimal-but-real auto-mounting editor
// (Path A). The extension registry, custom extensions, toolbar, theming, and
// explicit-init (Path B) build on top of this.
import { Editor, StarterKit } from "./tiptap-runtime";
import "./styles.css";

interface TipTapConfig {
  height?: string;
  manualMount?: boolean;
  [key: string]: unknown;
}

const CONFIG_ATTR = "data-tiptap-config";
const BOUND_ATTR = "data-tiptap-bound";

const instances = new Map<string, Editor>();
let uid = 0;

function ensureId(textarea: HTMLTextAreaElement): string {
  if (!textarea.id) {
    textarea.id = `tiptap-${++uid}`;
  }
  return textarea.id;
}

function readConfig(textarea: HTMLTextAreaElement): TipTapConfig {
  const raw = textarea.getAttribute(CONFIG_ATTR);
  if (!raw) {
    return {};
  }
  try {
    return JSON.parse(raw) as TipTapConfig;
  } catch (err) {
    console.error("[DjangoTipTap] invalid data-tiptap-config JSON", err);
    return {};
  }
}

function buildExtensions(_config: TipTapConfig) {
  // StarterKit baseline for now. config.extensions will later be resolved
  // through the extension registry (custom paragraph, font-size,
  // background-color, …).
  return [StarterKit];
}

function init(element: HTMLTextAreaElement, config: TipTapConfig = {}): Editor {
  const id = ensureId(element);
  const existing = instances.get(id);
  if (existing) {
    return existing;
  }

  const mount = document.createElement("div");
  mount.className = "django-tiptap";
  if (config.height) {
    mount.style.setProperty("--tiptap-height", config.height);
  }
  element.style.display = "none";
  element.parentNode?.insertBefore(mount, element.nextSibling);

  const editor = new Editor({
    element: mount,
    extensions: buildExtensions(config),
    content: element.value || "",
    onUpdate({ editor }) {
      element.value = editor.getHTML();
    },
  });

  element.setAttribute(BOUND_ATTR, "true");
  instances.set(id, editor);
  return editor;
}

function get(id: string): Editor | null {
  return instances.get(id) ?? null;
}

function destroy(id: string): void {
  const editor = instances.get(id);
  if (!editor) {
    return;
  }
  editor.destroy();
  instances.delete(id);
}

// Idempotent: mounts every unbound textarea[data-tiptap-config] under `root`.
function autoMount(root: ParentNode = document): void {
  const selector = `textarea[${CONFIG_ATTR}]:not([${BOUND_ATTR}])`;
  root.querySelectorAll<HTMLTextAreaElement>(selector).forEach((textarea) => {
    init(textarea, readConfig(textarea));
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => autoMount());
} else {
  autoMount();
}
// Django admin inline + htmx swaps (Path A re-scan).
document.addEventListener("formset:added", () => autoMount());
document.addEventListener("django:added", () => autoMount());
document.addEventListener("htmx:afterSwap", () => autoMount());

const DjangoTipTap = {
  version: "0.0.0",
  init,
  get,
  destroy,
  autoMount,
  // Re-exported primitives for extension authors (expanded as extensions land).
  tiptap: { Editor },
};

declare global {
  interface Window {
    DjangoTipTap: typeof DjangoTipTap;
  }
}
window.DjangoTipTap = DjangoTipTap;

export default DjangoTipTap;
