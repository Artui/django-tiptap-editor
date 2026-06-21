// Theming tiers 2 & 3 — region + shell renderers (semi-stable / experimental).
//
// Tier 1 (design tokens + the button registry) lives in ui.ts; this module is
// the next two tiers down the stability ladder:
//
//   Tier 2 — region renderers. ui.setRenderer(region, fn) replaces ONE chrome
//            region while the rest of the shell stays default. fn(ctx) returns a
//            DOM node that IS the region (a full replacement, not a wrapper).
//   Tier 3 — shell renderer. ui.setShellRenderer(fn) hands the consumer the
//            whole editor shell; fn(ctx) returns the shell root and must place
//            ctx.content (the ProseMirror host) somewhere inside it.
//
// Renderers are module-global and must be registered BEFORE auto-mount, exactly
// like extensions and buttons (see the load-order note in the docs).
import type { TipTapConfig } from "./default-config";
import type { Translator } from "./i18n";
import type { Editor } from "./tiptap-runtime";
import { getButton } from "./toolbar/button-registry";
import type { ButtonSpec } from "./toolbar/button-registry";

// Chrome regions the shell lays out today. Selection-anchored menus
// (bubbleMenu / floatingMenu) are reserved but not yet wired — registering one
// warns rather than silently doing nothing (see DEFERRED_REGIONS).
export type Region = "toolbar" | "statusbar";

const SHELL_REGIONS = new Set<Region>(["toolbar", "statusbar"]);
const DEFERRED_REGIONS = new Set<string>(["bubbleMenu", "floatingMenu"]);

// Passed to a region renderer. Exposes the editor, its config, the active
// translator, and a resolver for registered toolbar buttons so a custom region
// can reuse built-in controls.
export interface RegionContext {
  editor: Editor;
  config: TipTapConfig;
  t: Translator;
  getButton: (key: string) => ButtonSpec | undefined;
}

// Passed to the shell renderer. Adds `content` — the ProseMirror host element the
// consumer MUST insert somewhere into the returned shell, or the editor is
// invisible.
export interface ShellContext extends RegionContext {
  content: HTMLElement;
}

export type RegionRenderer = (ctx: RegionContext) => HTMLElement;
export type ShellRenderer = (ctx: ShellContext) => HTMLElement;

const regionRenderers = new Map<Region, RegionRenderer>();
let shellRenderer: ShellRenderer | null = null;

export function setRenderer(region: string, fn: RegionRenderer): void {
  if (DEFERRED_REGIONS.has(region)) {
    console.warn(
      `[DjangoTipTap] ui.setRenderer("${region}", …) is not supported yet — ` +
        "bubbleMenu / floatingMenu (selection-anchored) are a planned follow-up.",
    );
    return;
  }
  if (!SHELL_REGIONS.has(region as Region)) {
    console.error(
      `[DjangoTipTap] ui.setRenderer: unknown region "${region}" ` +
        '(expected "toolbar" | "statusbar").',
    );
    return;
  }
  regionRenderers.set(region as Region, fn);
}

export function getRenderer(region: Region): RegionRenderer | undefined {
  return regionRenderers.get(region);
}

export function setShellRenderer(fn: ShellRenderer): void {
  shellRenderer = fn;
}

export function getShellRenderer(): ShellRenderer | null {
  return shellRenderer;
}

// Builds the RegionContext shared by region and shell renderers.
export function rendererContext(editor: Editor, config: TipTapConfig, t: Translator): RegionContext {
  return { editor, config, t, getButton };
}
