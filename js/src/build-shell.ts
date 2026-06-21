// Assembles an editor's shell: the default chrome (toolbar → content →
// optional statusbar), unless a consumer has overridden a region (tier 2) or the
// whole shell (tier 3) via DjangoTipTap.ui. Selection-anchored menus
// (bubbleMenu / floatingMenu) are mounted as overlays on whichever shell results.
// The returned refresh() syncs only the chrome this module owns — the built-in
// toolbar's button states. Custom regions and shells own their own reactivity.
import { mountFloatingMenu } from "./floating-menu";
import { FLOATING_REGIONS, getRenderer, getShellRenderer, rendererContext } from "./renderers";
import type { RegionContext } from "./renderers";
import type { TipTapConfig } from "./default-config";
import type { Translator } from "./i18n";
import type { Editor } from "./tiptap-runtime";
import { renderToolbar } from "./toolbar/render-toolbar";

export interface BuiltShell {
  el: HTMLElement;
  refresh: () => void;
}

const NOOP = (): void => {};

// Mount any registered selection-anchored menus as overlays on the shell.
function mountFloatingMenus(editor: Editor, shell: HTMLElement, ctx: RegionContext): void {
  for (const kind of FLOATING_REGIONS) {
    const renderer = getRenderer(kind);
    if (renderer) {
      mountFloatingMenu(editor, shell, kind, renderer(ctx));
    }
  }
}

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
    const el = shellRenderer({ ...ctx, content });
    mountFloatingMenus(editor, el, ctx);
    return { el, refresh: NOOP };
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

  mountFloatingMenus(editor, shell, ctx);
  return { el: shell, refresh };
}
