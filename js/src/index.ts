// window.DjangoTipTap — the public glue entry. In place today: the build
// pipeline, the runtime seam, the fidelity extension set, the extension
// registry, a clickable toolbar + button registry, design-token theming,
// region/shell renderers, i18n, source view, dropdown controls, and Path-A
// auto-mount. Explicit-init (Path B) layers on later.
import { buildExtensions } from "./build-extensions";
import { buildShell } from "./build-shell";
import { htmlToJSON, htmlToStored, renderHTML } from "./convert";
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
const STORAGE_ATTR = "data-tiptap-storage";
// Marks an editor's shell root. Lets the lifecycle observer cheaply ignore
// ProseMirror's own DOM churn (mutations inside a shell) instead of treating
// every keystroke as a potential mount/unmount.
const SHELL_ATTR = "data-tiptap-shell";

// Re-exported primitives for extension authors (no bundler of their own needed).
const tiptap = { Editor, Extension, Mark, Node, mergeAttributes };

interface Instance {
  editor: Editor;
  shell: HTMLElement;
  // The textarea this editor is bound to. Tracked so liveness can be checked
  // against the live DOM (document.contains) rather than trusting the map — a
  // destructive DOM swap can remove the node without ever calling destroy().
  element: HTMLTextAreaElement;
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

// JSON storage mode: the textarea holds a {doc, html} envelope. Use the doc when
// it has content; otherwise fall back to the html mirror (so a record seeded with
// only legacy HTML — e.g. a migration that copied a TinyMCE column into the
// mirror — is still editable, and converts to a real doc on first save). "" for
// an empty/invalid field (a fresh form), so the editor starts blank.
function readInitialContent(raw: string): object | string {
  if (!raw) {
    return "";
  }
  try {
    const env = JSON.parse(raw) as { doc?: { content?: unknown[] }; html?: string };
    if (env.doc && Array.isArray(env.doc.content) && env.doc.content.length > 0) {
      return env.doc;
    }
    return typeof env.html === "string" ? env.html : "";
  } catch (err) {
    console.error("[DjangoTipTap] invalid JSON-storage value", err);
    return "";
  }
}

function init(element: HTMLTextAreaElement, config: TipTapConfig = {}): Editor {
  const id = ensureId(element);
  const existing = instances.get(id);
  if (existing) {
    // Honor the cached instance only while its textarea is still in the live
    // DOM. A destructive swap can replace the field with a fresh textarea that
    // reuses the same id (Django emits a stable id_<field>), leaving the old
    // node and its shell detached. Trusting the map here would return a dead
    // editor and leave the new textarea unbound, so evict the stale instance and
    // fall through to mount on the new element.
    if (document.contains(existing.element)) {
      return existing.editor;
    }
    destroy(id);
  }

  const content = document.createElement("div");
  content.className = "django-tiptap__content";

  const locale = config.locale ?? "en";
  const t = getTranslator(locale);
  const ctx: ExtensionContext = { tiptap, locale, t };

  // Storage mode: "html" writes editor.getHTML() back into the textarea; "json"
  // writes a {doc, html} envelope (TipTapJSONField). Driven by the data-* attr
  // the widget emits; defaults to html for hand-mounted / Path-B elements.
  const json = element.getAttribute(STORAGE_ATTR) === "json";

  const editor = new Editor({
    element: content,
    extensions: buildExtensions(config, ctx),
    content: json ? readInitialContent(element.value) : element.value || "",
    onUpdate({ editor }) {
      const html = editor.getHTML();
      element.value = json
        ? JSON.stringify({ doc: editor.getJSON(), html })
        : html;
      config.onChange?.(html);
    },
  });
  // Make the translator + config resolvable from any onClick(editor) / control.
  setTranslator(editor, t);
  setEditorConfig(editor, config);
  wireImageDropPaste(editor);

  // Default chrome, or a consumer's region / shell override (see build-shell).
  const shell = buildShell(editor, config, content, t);
  shell.el.setAttribute(SHELL_ATTR, id);
  if (config.height) {
    shell.el.style.setProperty("--tiptap-height", config.height);
  }

  element.style.display = "none";
  element.parentNode?.insertBefore(shell.el, element.nextSibling);
  shell.refresh();
  editor.on("transaction", () => shell.refresh());

  element.setAttribute(BOUND_ATTR, "true");
  instances.set(id, { editor, shell: shell.el, element });
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

// Tear down every editor whose textarea lives inside `root`. Called when content
// is about to be removed from the DOM, so an editor's shell and ProseMirror view
// don't linger as orphans when a swap drops the field without re-rendering it.
// Deleting the current key mid-iteration is safe for a Map's iterator.
function destroyWithin(root: Element): void {
  for (const [id, instance] of instances) {
    if (root === instance.element || root.contains(instance.element)) {
      destroy(id);
    }
  }
}

// Idempotent: mounts every unbound textarea[data-tiptap-config] at or under
// `root`. The observer can hand us a swapped-in textarea directly (not just a
// container), so the root itself is checked, not only its descendants.
function autoMount(root: ParentNode = document): void {
  const selector = `textarea[${CONFIG_ATTR}]:not([${BOUND_ATTR}])`;
  if (root instanceof HTMLTextAreaElement && root.matches(selector)) {
    init(root, readConfig(root));
  }
  root.querySelectorAll<HTMLTextAreaElement>(selector).forEach((textarea) => {
    init(textarea, readConfig(textarea));
  });
}

// Framework-agnostic mount / teardown. A single MutationObserver reacts to ANY
// DOM change — htmx, Turbo, Unpoly, Livewire, Alpine, Django admin inlines, or
// hand-rolled JS — so no per-framework event wiring is needed. Added subtrees are
// scanned for unmounted editors; removed subtrees have their editors torn down.
// Mutations inside an editor's own shell (ProseMirror's DOM churn on every
// keystroke) are skipped, so the observer stays cheap on a live page.
function observeDom(): void {
  const observer = new MutationObserver((records) => {
    const added: Element[] = [];
    const removed: Element[] = [];
    for (const record of records) {
      const target = record.target;
      if (target instanceof Element && target.closest(`[${SHELL_ATTR}]`)) {
        continue; // a mutation inside an editor — not a mount/unmount site
      }
      record.removedNodes.forEach((node) => {
        if (node instanceof Element) {
          removed.push(node);
        }
      });
      record.addedNodes.forEach((node) => {
        if (node instanceof Element && !node.hasAttribute(SHELL_ATTR)) {
          added.push(node); // skip our own shells; they hold no unmounted editor
        }
      });
    }
    // Teardown before mount: an element removed and re-added in the same batch
    // (a move) must not be destroyed and then skipped on re-mount.
    if (instances.size) {
      removed.forEach((node) => {
        if (!node.isConnected) {
          destroyWithin(node);
        }
      });
    }
    added.forEach((node) => {
      if (node.isConnected) {
        autoMount(node);
      }
    });
  });
  observer.observe(document.body, { childList: true, subtree: true });
}

// One-time bootstrap: register chrome, scan the initial DOM, and start the
// lifecycle observer. Guarded (see the bottom of the file) so a re-executed
// bundle doesn't run it twice. The observer needs document.body, so when the
// script runs in <head> during parsing we defer both to DOMContentLoaded.
function bootstrap(): void {
  registerBuiltInButtons();
  checkTipTapVersion();

  const start = (): void => {
    autoMount();
    observeDom();
  };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
}

const DjangoTipTap = {
  version: "0.0.0",
  supportedTipTapVersion: SUPPORTED_TIPTAP_VERSION,
  init,
  get,
  destroy,
  autoMount,
  registerExtension,
  registerLocale,
  htmlToJSON,
  renderHTML,
  htmlToStored,
  ui,
  tiptap,
};

declare global {
  interface Window {
    DjangoTipTap: typeof DjangoTipTap;
  }
}

// A second execution of the bundle must be a no-op. If the asset is injected and
// run more than once (e.g. a framework re-inserts the script tag inside swapped-in
// content), a re-run of this classic-script IIFE would build a fresh, empty glue
// module — new instances map, new listeners — and clobber the live one, orphaning
// every mounted editor. Bail if we're already installed and keep the first module.
// (Read through a cast: the ambient type declares the property as always-present
// for consumers, but at this point it may genuinely be undefined.)
const alreadyMounted = (window as { DjangoTipTap?: typeof DjangoTipTap }).DjangoTipTap;
if (!alreadyMounted) {
  window.DjangoTipTap = DjangoTipTap;
  bootstrap();
}

export type {
  RegionContext,
  RegionRenderer,
  ShellContext,
  ShellRenderer,
} from "./renderers";
export type { ExtensionContext, ExtensionFactory, TipTapConfig };
export default DjangoTipTap;
