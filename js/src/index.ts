// window.DjangoTipTap — the public glue entry. In place today: the build
// pipeline, the runtime seam, the fidelity extension set, the extension
// registry, a clickable toolbar + button registry, design-token theming,
// region/shell renderers, i18n, source view, dropdown controls, and Path-A
// auto-mount. Explicit-init (Path B) layers on later.
import { buildExtensions } from "./build-extensions";
import { buildShell } from "./build-shell";
import type { TipTapConfig } from "./default-config";
import { setEditorConfig } from "./editor-config";
import { getTranslator, registerLocale, setTranslator } from "./i18n";
import { registerExtension } from "./registry";
import { wireImageDropPaste } from "./upload";
import type { ExtensionContext, ExtensionFactory } from "./registry";
import { registerBuiltInButtons } from "./toolbar/built-in-buttons";
import { Editor, Extension, Mark, Node, mergeAttributes } from "./tiptap-runtime";
import { ui } from "./ui";
import { checkTipTapVersion, SUPPORTED_TIPTAP_VERSION } from "./version-check";
import "./styles.css";

const CONFIG_ATTR = "data-tiptap-config";
const BOUND_ATTR = "data-tiptap-bound";

registerBuiltInButtons();
checkTipTapVersion();

// Re-exported primitives for extension authors (no bundler of their own needed).
const tiptap = { Editor, Extension, Mark, Node, mergeAttributes };

interface Instance {
  editor: Editor;
  shell: HTMLElement;
}

const instances = new Map<string, Instance>();
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

function init(element: HTMLTextAreaElement, config: TipTapConfig = {}): Editor {
  const id = ensureId(element);
  const existing = instances.get(id);
  if (existing) {
    return existing.editor;
  }

  const content = document.createElement("div");
  content.className = "django-tiptap__content";

  const locale = config.locale ?? "en";
  const t = getTranslator(locale);
  const ctx: ExtensionContext = { tiptap, locale, t };

  const editor = new Editor({
    element: content,
    extensions: buildExtensions(config, ctx),
    content: element.value || "",
    onUpdate({ editor }) {
      const html = editor.getHTML();
      element.value = html;
      config.onChange?.(html);
    },
  });
  // Make the translator + config resolvable from any onClick(editor) / control.
  setTranslator(editor, t);
  setEditorConfig(editor, config);
  wireImageDropPaste(editor);

  // Default chrome, or a consumer's region / shell override (see build-shell).
  const shell = buildShell(editor, config, content, t);
  if (config.height) {
    shell.el.style.setProperty("--tiptap-height", config.height);
  }

  element.style.display = "none";
  element.parentNode?.insertBefore(shell.el, element.nextSibling);
  shell.refresh();
  editor.on("transaction", () => shell.refresh());

  element.setAttribute(BOUND_ATTR, "true");
  instances.set(id, { editor, shell: shell.el });
  return editor;
}

function get(id: string): Editor | null {
  return instances.get(id)?.editor ?? null;
}

function destroy(id: string): void {
  const instance = instances.get(id);
  if (!instance) {
    return;
  }
  instance.editor.destroy();
  instance.shell.remove();
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
  supportedTipTapVersion: SUPPORTED_TIPTAP_VERSION,
  init,
  get,
  destroy,
  autoMount,
  registerExtension,
  registerLocale,
  ui,
  tiptap,
};

declare global {
  interface Window {
    DjangoTipTap: typeof DjangoTipTap;
  }
}
window.DjangoTipTap = DjangoTipTap;

export type {
  RegionContext,
  RegionRenderer,
  ShellContext,
  ShellRenderer,
} from "./renderers";
export type { ExtensionContext, ExtensionFactory, TipTapConfig };
export default DjangoTipTap;
