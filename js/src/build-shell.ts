// Assembles an editor's shell: the default chrome (toolbar → content →
// optional statusbar), unless a consumer has overridden a region (tier 2) or the
// whole shell (tier 3) via DjangoTipTap.ui. The returned refresh() syncs only
// the chrome this module owns — the built-in toolbar's button states. Custom
// regions and shells own their own reactivity off the editor in ctx.
import type { TipTapConfig } from "./default-config";
import type { Translator } from "./i18n";
import {
  getRenderer,
  getShellRenderer,
  rendererContext,
} from "./renderers";
import type { Editor } from "./tiptap-runtime";
import { renderToolbar } from "./toolbar/render-toolbar";

export interface BuiltShell {
  el: HTMLElement;
  refresh: () => void;
}

const NOOP = (): void => {};

export function buildShell(
  editor: Editor,
  config: TipTapConfig,
  content: HTMLElement,
  t: Translator,
): BuiltShell {
  const ctx = rendererContext(editor, config, t);

  // Tier 3 — the consumer owns the whole shell. They must place `content`
  // themselves; we own no chrome here, so refresh is a no-op.
  const shellRenderer = getShellRenderer();
  if (shellRenderer) {
    return { el: shellRenderer({ ...ctx, content }), refresh: NOOP };
  }

  const shell = document.createElement("div");
  shell.className = "django-tiptap";

  // Toolbar region (top) — custom replacement or the default built-in toolbar.
  let refresh: () => void = NOOP;
  const toolbarRenderer = getRenderer("toolbar");
  if (toolbarRenderer) {
    shell.appendChild(toolbarRenderer(ctx));
  } else {
    const toolbar = renderToolbar(editor, config);
    shell.appendChild(toolbar.el);
    refresh = toolbar.refresh;
  }

  // Editing surface (middle).
  shell.appendChild(content);

  // Statusbar region (bottom) — opt-in: nothing renders unless registered.
  const statusbarRenderer = getRenderer("statusbar");
  if (statusbarRenderer) {
    shell.appendChild(statusbarRenderer(ctx));
  }

  return { el: shell, refresh };
}
